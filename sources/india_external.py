"""India's external accounts from the DBIE mirror: monthly merchandise trade,
the quarterly balance of payments, and FPI flows if a slug exists for them.

WHY THIS MODULE EXISTS. Three series are blocking real work:

  MONTHLY IMPORTS  the denominator of import cover. Without it there is no
                   cover series at all, however good the reserve data is.
  BoP OVERALL      the published quarterly balance. A monthly change in
                   reserves proxies it but still carries valuation effects
                   (gold, EUR/JPY translation) that RBI strips out.
  FPI HISTORY      NSDL refuses historical postbacks, so the flows file holds
                   the current year only.

THE HOST. `dbie.rbihub.in/data/{slug}.json`, the same mirror rbihub.py already
pulls REER, forward premia and intervention from successfully. An earlier
version of this file guessed at `data.rbi.org.in/DBIE/api/...` — which is the
empty JavaScript shell rbihub.py's own docstring warns about, so it could never
have worked. Copy a proven pattern; do not invent one.

Same provenance caveat as rbihub: this is a pre-rendered mirror, known to go
stale and known to have served at least one truncated payload. Backfill and
history only.

DISCOVERY FIRST, THEN FETCH. The slugs are not documented anywhere, and
guessing them is what wasted the last attempt. So this module first pulls the
catalogue, archives it, and searches it for anything trade- or
balance-of-payments-shaped. Whatever it finds is written into the manifest, so
even a run that retrieves no data tells the next run exactly which slugs exist.
"""
from __future__ import annotations

import json
import re

from .common import (DQ, Deadline, FetchError, archive_raw, get,
                     guard_regression, num, read_existing, write_csv)

NAME = "india_external"
BASE = "https://dbie.rbihub.in/data/{}.json"
# Catalogue endpoints, tried in order. None is documented; all are archived.
CATALOGUES = ["https://dbie.rbihub.in/data/index.json",
              "https://dbie.rbihub.in/data/catalogue.json",
              "https://dbie.rbihub.in/api/catalogue",
              "https://dbie.rbihub.in/data/manifest.json"]

WANTED = {
    "trade": (re.compile(r"trade|import|export|merchandi", re.I),
              "india/trade_monthly.csv", "monthly merchandise trade"),
    "bop": (re.compile(r"balance.of.payment|\bbop\b|current.account", re.I),
            "india/bop_quarterly.csv", "quarterly balance of payments"),
    "fpi": (re.compile(r"\bfpi\b|\bfii\b|foreign.portfolio", re.I),
            "india/fpi_flows_dbie.csv", "foreign portfolio flows"),
}

# Slugs worth trying even if the catalogue cannot be read. Named after the
# pattern rbihub's working slugs follow.
FALLBACK_SLUGS = {
    "trade": ["sdmx-india-s-foreign-trade", "india-s-foreign-trade",
              "sdmx-foreign-trade", "foreign-trade"],
    "bop": ["sdmx-balance-of-payments", "balance-of-payments",
            "sdmx-india-s-balance-of-payments", "overall-balance-of-payments"],
    "fpi": ["sdmx-foreign-portfolio-investment", "foreign-portfolio-investment"],
}


def _catalogue(dq: DQ) -> list[str]:
    """Every slug the mirror admits to having. Archived so a failed run still
    leaves behind the information needed to fix the next one."""
    for url in CATALOGUES:
        try:
            raw = get(url, tries=1, timeout=30)
        except FetchError:
            continue
        archive_raw(f"india_external/catalogue_{url.rsplit('/', 1)[-1]}", raw)
        try:
            doc = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        slugs = re.findall(r'"(?:slug|id|name|key)"\s*:\s*"([a-z0-9][a-z0-9\-_]{4,})"',
                           raw.decode("utf-8", "replace"), re.I)
        if slugs:
            dq.note(NAME, f"catalogue {url} listed {len(set(slugs))} slugs")
            return sorted(set(slugs))
    dq.warn(NAME, "no catalogue endpoint responded with JSON — falling back to "
                  "a guessed slug list; check raw/india_external/ for what the "
                  "mirror actually returned")
    return []


def _rows_from(obj) -> list[dict]:
    """Mirror payloads come in two shapes: a column-major {columns, dates,
    values} table, or a plain list of records nested somewhere. rbihub.py
    handles both; the same logic is repeated here rather than imported, because
    that module's helpers are private to it."""
    if isinstance(obj, dict) and obj.get("dates") and obj.get("values"):
        cols, dates, vals = (obj.get("columns") or [], obj["dates"], obj["values"])
        out = []
        for i, d in enumerate(dates):
            row = {"date": d}
            for j, c in enumerate(cols):
                key = c if isinstance(c, str) else (
                    c.get("code") or c.get("label") or f"c{j}")
                try:
                    row[str(key)] = vals[j][i]
                except (IndexError, TypeError):
                    row[str(key)] = ""
            out.append(row)
        return out
    best: list = []
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, list) and o and isinstance(o[0], dict) and len(o) > len(best):
            best = o
        elif isinstance(o, dict):
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(x for x in o if isinstance(x, (dict, list)))
    return [{str(k): ("" if v is None else v) for k, v in r.items()} for r in best]


def _try(slug: str, dq: DQ) -> list[dict] | None:
    try:
        raw = get(BASE.format(slug), tries=1, timeout=40)
    except FetchError:
        return None
    archive_raw(f"india_external/{slug}.json", raw)
    try:
        rows = _rows_from(json.loads(raw))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return rows if len(rows) >= 12 else None


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    slugs = _catalogue(dq)
    files, out = [], {}

    for key, (pat, path, label) in WANTED.items():
        if deadline and deadline.expired:
            dq.warn(NAME, f"{label}: skipped, out of time budget")
            continue

        cands = [s for s in slugs if pat.search(s)] or FALLBACK_SLUGS[key]
        if slugs and not [s for s in slugs if pat.search(s)]:
            dq.warn(NAME, f"{label}: catalogue has no slug matching "
                          f"/{pat.pattern}/ — the mirror may simply not carry "
                          f"it; trying guesses anyway")
        out[f"{key}_candidates"] = cands[:8]

        rows = None
        for s in cands[:6]:
            if deadline and deadline.expired:
                break
            rows = _try(s, dq)
            if rows:
                dq.note(NAME, f"{label}: slug '{s}' returned {len(rows)} rows")
                out[f"{key}_slug"] = s
                break
        if not rows:
            dq.warn(NAME, f"{label}: no slug returned usable data. Tried "
                          f"{cands[:6]}. Every response is archived under "
                          f"raw/india_external/ — read those before guessing "
                          f"again.")
            continue

        # Merge on the date key rather than overwrite, so a truncated payload
        # cannot silently shorten the file.
        prior = {r.get("date", ""): r for r in read_existing(path)}
        for r in rows:
            d = str(r.get("date") or r.get("period") or r.get("TIME_PERIOD") or "")
            if d:
                r["date"] = d
                prior[d] = r
        merged = [prior[k] for k in sorted(prior) if k]
        if not guard_regression(dq, NAME, path, merged):
            continue
        fields = ["date"] + sorted({k for r in merged for k in r} - {"date"})
        write_csv(path, [{f: r.get(f, "") for f in fields} for r in merged], fields)
        files.append("data/" + path)
        out[f"{key}_rows"] = len(merged)
        out[f"{key}_last"] = merged[-1]["date"]
        dq.note(NAME, f"{label}: {len(merged)} rows on file, last "
                      f"{merged[-1]['date']}, columns {fields[1:6]}")

    if not files:
        raise FetchError(
            "india_external: nothing retrieved. This is the EXPECTED first-run "
            "outcome if the slugs differ — the point of this run is the "
            "archived catalogue and payloads under raw/india_external/, which "
            "name the slugs that do exist. Read them, set them, run again.")
    out["files"] = files
    return out
