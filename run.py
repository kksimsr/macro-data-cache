#!/usr/bin/env python3
"""Orchestrator. Runs every source, writes a manifest, exits non-zero if anything
is broken — while still committing whatever succeeded.

House rule: data-quality problems are LOUD and never silent. A source that fails
does not quietly disappear from the dataset; it shows up as an error in
logs/manifest.json and MANIFEST.md, and it fails the workflow run so the failure
is visible in the Actions tab rather than discovered months later in a backtest.

Usage:
    python run.py                 # everything
    python run.py --only fred     # one source
    python run.py --skip nse_iv   # all but one
    python run.py --list          # show source names
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from sources import fred, india_misc, nsdl_fpi, rbi_forward_book, rbi_wss, rbihub
from sources.common import DQ, LOGS, ROOT, Deadline

# name -> (module, description, time budget in seconds)
#
# Budgets exist because the first live run died on the job timeout with nothing
# committed. Sources stop fetching when their budget is spent and keep what they
# have; capped backfill then completes over consecutive daily runs. The global
# budget is deliberately below the workflow step timeout so the commit step
# always gets to run.
SOURCES = {
    "fred": (fred, "FRED — global/US, EM crosses, DXY constituents", 300),
    "rbi_forward_book": (rbi_forward_book, "RBI IRFCL — net forward book", 420),
    "rbi_wss": (rbi_wss, "RBI WSS — weekly FX reserves", 360),
    "rbihub": (rbihub, "DBIE mirror — REER, forward premia, intervention, ECB", 180),
    "nsdl_fpi": (nsdl_fpi, "NSDL — monthly FPI flows", 300),
    "india_misc": (india_misc, "WPI, gold, NSE USD/INR option IV", 180),
}

GLOBAL_BUDGET_S = 1500   # 25 min; workflow step timeout is 30 min


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

    finished = datetime.now(timezone.utc)
    manifest = {
        "run_started_utc": started.isoformat(timespec="seconds"),
        "run_finished_utc": finished.isoformat(timespec="seconds"),
        "duration_s": round((finished - started).total_seconds(), 1),
        "sources": results,
        "dq": {"errors": dq.n_errors, "warnings": dq.n_warns, "entries": dq.entries},
    }
    LOGS.mkdir(exist_ok=True)
    (LOGS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_markdown(manifest)

    ok = sum(1 for r in results.values() if r["status"] == "ok")
    print(f"\n{'='*66}\n{ok}/{len(results)} sources ok · "
          f"{dq.n_errors} errors · {dq.n_warns} warnings")
    if dq.n_errors:
        print("FAILING THE RUN so the problem is visible. Data that did succeed "
              "is still committed.")
        return 1
    return 0


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
    if "series" in m["sources"].get("fred", {}):
        L += ["", "## FRED coverage", "", "| id | label | n | first | last |",
              "|---|---|---|---|---|"]
        for sid, s in m["sources"]["fred"]["series"].items():
            L.append(f"| `{sid}` | {s['label']} | {s['n']} | {s['first']} | {s['last']} |")
    (Path(ROOT) / "MANIFEST.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
