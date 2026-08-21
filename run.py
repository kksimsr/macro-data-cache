#!/usr/bin/env python3
"""Orchestrator. Runs every source, writes a manifest, exits non-zero if anything
is broken — while still committing whatever succeeded.

House rule: data-quality problems are LOUD and never silent. A source that fails
does not quietly disappear from the dataset; it shows up as an error in
logs/manifest.json and MANIFEST.md, and it fails the workflow run so the failure
is visible in the Actions tab rather than discovered months later in a backtest.

Usage:
    python run.py                 # everything
    python run.py --only market   # one source
    python run.py --skip nse_iv   # all but one
    python run.py --list          # show source names
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from sources import (india_misc, market, nsdl_fpi, rbi_forward_book, rbi_wss,
                     rbihub)
from sources.common import DQ, LOGS, ROOT, Deadline

# name -> (module, description, time budget in seconds)
#
# Budgets exist because the first live run died on the job timeout with nothing
# committed. Sources stop fetching when their budget is spent and keep what they
# have; capped backfill then completes over consecutive daily runs. The global
# budget is deliberately below the workflow step timeout so the commit step
# always gets to run.
# india_misc runs FIRST: the NSE implied-vol capture is the only irreplaceable
# item here (no historical source exists, so a missed day is a permanent hole).
# It must not be the one starved when the clock runs down.
# Budgets sum to <= GLOBAL_BUDGET_S; previously they summed to 1800 against a
# 1500 cap, so the ordering silently decided who got squeezed.
SOURCES = {
    "india_misc": (india_misc, "WPI + NSE USD/INR option IV (append-only)", 150),
    "market": (market, "GitHub mirrors + FRED — FX, oil, VIX, US rates", 330),
    "rbi_forward_book": (rbi_forward_book, "RBI IRFCL — net forward book", 360),
    "rbi_wss": (rbi_wss, "RBI WSS — weekly FX reserves", 330),
    "rbihub": (rbihub, "DBIE mirror — REER, forward premia, intervention, ECB", 150),
    "nsdl_fpi": (nsdl_fpi, "NSDL — monthly FPI flows", 180),
}

GLOBAL_BUDGET_S = 1500   # 25 min; workflow step timeout is 30 min
assert sum(b for _m, _d, b in SOURCES.values()) <= GLOBAL_BUDGET_S

# DEEP mode: drain the whole backlog in one run instead of a slice a day.
#
# The daily budget is sized for a steady state where each run picks up a handful
# of new observations. It is the wrong shape for the initial fill: the forward
# book spent 27s of its 360s budget fetching 31 months, so the thing rationing
# the backfill was the per-run CAP, not the clock, and a 25-year series was going
# to take a fortnight of nightly runs for no reason. Setting DEEP=1 lifts the
# caps and the clock together, for a manually dispatched run. The job timeout is
# 60 min, so the step gets 50 min and the fetch budget 47.5.
DEEP = os.environ.get("DEEP", "").strip() not in ("", "0", "false", "False")
if DEEP:
    GLOBAL_BUDGET_S = 2850
    SOURCES = {**SOURCES,
               "rbi_forward_book": SOURCES["rbi_forward_book"][:2] + (1200,),
               "rbi_wss": SOURCES["rbi_wss"][:2] + (900,),
               "market": SOURCES["market"][:2] + (300,),
               "nsdl_fpi": SOURCES["nsdl_fpi"][:2] + (120,)}
    assert sum(b for _m, _d, b in SOURCES.values()) <= GLOBAL_BUDGET_S


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--skip", action="append", default=[])
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for k, (_m, d, b) in SOURCES.items():
            print(f"{k:20s} {b:>5}s  {d}")
        return 0

    names = args.only or [k for k in SOURCES if k not in args.skip]
    unknown = [n for n in names if n not in SOURCES]
    if unknown:
        print(f"unknown source(s): {unknown}", file=sys.stderr)
        return 2

    dq = DQ()
    started = datetime.now(timezone.utc)
    results: dict[str, dict] = {}
    overall = Deadline(GLOBAL_BUDGET_S)

    for name in names:
        mod, desc, budget = SOURCES[name]
        allowed = min(budget, overall.remaining)
        print(f"\n=== {name} :: {desc}  [budget {allowed:.0f}s, "
              f"{overall.remaining:.0f}s left overall]", flush=True)
        if allowed <= 5:
            results[name] = {"status": "skipped", "error": "out of time budget"}
            dq.warn(name, "skipped: global time budget exhausted this run")
            continue
        t0 = overall.elapsed
        try:
            results[name] = {"status": "ok",
                             **(mod.run(dq, deadline=Deadline(allowed)) or {})}
        except Exception as e:  # noqa: BLE001
            results[name] = {"status": "failed", "error": f"{type(e).__name__}: {e}"}
            dq.error(name, f"source failed: {type(e).__name__}: {e}")
            traceback.print_exc()
        results[name]["seconds"] = round(overall.elapsed - t0, 1)
        # Persist after EVERY source. Writing the manifest only at the end meant a
        # step timeout committed fresh CSVs alongside the previous run's manifest,
        # which then described a dataset that no longer existed.
        _persist(started, results, dq)

    # One writer for the manifest: _persist merges with what is already on disk,
    # so a --only run records that source without erasing the other five.
    _persist(started, results, dq)

    ok = sum(1 for r in results.values() if r["status"] == "ok")
    print(f"\n{'='*66}\n{ok}/{len(results)} sources ok · "
          f"{dq.n_errors} errors · {dq.n_warns} warnings")
    if dq.n_errors:
        print("FAILING THE RUN so the problem is visible. Data that did succeed "
              "is still committed.")
        return 1
    return 0


def _persist(started, results: dict, dq: DQ) -> None:
    now = datetime.now(timezone.utc)
    # Merge into any existing manifest so a --only run does not erase the record
    # of every other source.
    prior = {}
    f = LOGS / "manifest.json"
    if f.exists():
        try:
            prior = (json.loads(f.read_text()) or {}).get("sources", {})
        except (json.JSONDecodeError, OSError):
            prior = {}
    # Drop records for sources that no longer exist. `fred` was replaced by
    # `market`, but the merge kept resurrecting its run-2 FAILED row, so the
    # manifest reported a failure from a module that is no longer in the repo.
    merged = {k: v for k, v in {**prior, **results}.items() if k in SOURCES}
    m = {
        "run_started_utc": started.isoformat(timespec="seconds"),
        "run_finished_utc": now.isoformat(timespec="seconds"),
        "duration_s": round((now - started).total_seconds(), 1),
        "sources": merged,
        "dq": {"errors": dq.n_errors, "warnings": dq.n_warns, "entries": dq.entries},
    }
    _atomic_write(f, json.dumps(m, indent=2))
    _write_markdown(m)


def _write_markdown(m: dict) -> None:
    L = ["# Data manifest", "",
         f"Last run: **{m['run_finished_utc']}** · {m['duration_s']}s · "
         f"{m['dq']['errors']} errors, {m['dq']['warnings']} warnings", "",
         "| source | status | detail |", "|---|---|---|"]
    for name, r in m["sources"].items():
        if r["status"] == "ok":
            bits = []
            if "series" in r:
                bits.append(f"{len(r['series'])} series")
            for k in ("n", "n_months", "n_weeks", "parsed", "last",
                      "backfill_remaining", "seconds"):
                if k in r:
                    bits.append(f"{k}={r[k]}")
            if "files" in r and not bits:
                bits.append(f"{len(r['files'])} files")
            L.append(f"| `{name}` | ok | {', '.join(bits) or '—'} |")
        elif r["status"] == "skipped":
            L.append(f"| `{name}` | skipped | {r.get('error','')} |")
        else:
            L.append(f"| `{name}` | **FAILED** | {r.get('error','')} |")
    errs = [e for e in m["dq"]["entries"] if e["level"] == "error"]
    warns = [e for e in m["dq"]["entries"] if e["level"] == "warn"]
    if errs:
        L += ["", "## Errors", ""] + [f"- **{e['source']}** — {e['msg']}" for e in errs]
    if warns:
        L += ["", "## Warnings", ""] + [f"- *{e['source']}* — {e['msg']}" for e in warns]
    mk = m["sources"].get("market", {})
    if mk.get("gaps"):
        L += ["", "## Coverage gaps", "",
              "FRED-only series unavailable this run (no mirror exists); retried next run:",
              "", ", ".join(f"`{g}`" for g in mk["gaps"])]
    if "series" in mk:
        L += ["", "## Market coverage", "", "| id | label | n | first | last |",
              "|---|---|---|---|---|"]
        for sid, s in mk["series"].items():
            L.append(f"| `{sid}` | {s['label']} | {s['n']} | {s['first']} | {s['last']} |")
    _atomic_write(Path(ROOT) / "MANIFEST.md", "\n".join(L) + "\n")


def _atomic_write(path: Path, text: str) -> None:
    """The fetch step can be killed at any instant and the workflow commits
    whatever is on disk, so a half-written manifest must never land."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
