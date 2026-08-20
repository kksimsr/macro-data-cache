"""dbie.rbihub.in — JSON mirror of RBI's Database on Indian Economy.

IMPORTANT PROVENANCE CAVEAT. This host is run by the Reserve Bank Innovation Hub
(an RBI subsidiary) but its own docs describe it as a *static mirror pre-rendered
from scraped DBIE data* — not the live database. Observed problems: several months
of staleness, at least one catalogue description mismatched to its payload, and at
least one payload truncated to a stub.

So: use it for BACKFILL AND HISTORY ONLY, never as the system of record for a live
signal. Every series pulled here is stamped with its own last observation date and
staleness is flagged loudly. The official data.rbi.org.in/DBIE is an empty
JavaScript shell with no discoverable API, which is why this mirror exists at all.
"""
from __future__ import annotations

import json
from datetime import date

from .common import DQ, FetchError, archive_raw, get, write_csv

NAME = "rbihub"
BASE = "https://dbie.rbihub.in/data/{}.json"

# slug -> (output path, human label, max acceptable staleness in days)
SERIES = {
    "sdmx-indices-of-reer-neer-monthly": (
        "rbi/reer_neer_monthly.csv", "REER/NEER 40- and 6-currency, monthly", 120),
    "sdmx-forward-premia-inter-bank": (
        "rbi/forward_premia_monthly.csv", "USD/INR forward premia 1M/3M/6M", 120),
    "usd-sale-purchase": (
        "rbi/rbi_usd_intervention.csv", "RBI USD sale/purchase (spot intervention)", 200),
    "external-commercial-borrowings": (
        "rbi/ecb.csv", "External commercial borrowings", 200),
}


def _sdmx_to_rows(obj: dict) -> list[dict]:
    """The /tables/* payloads use {columns, dates, values} where values is a
    column-major list of lists."""
    cols = obj.get("columns") or []
    dates = obj.get("dates") or []
    vals = obj.get("values") or []
    rows = []
    for i, d in enumerate(dates):
        row = {"date": d}
        for j, c in enumerate(cols):
            key = c if isinstance(c, str) else (c.get("code") or c.get("label") or f"c{j}")
            try:
                v = vals[j][i]
            except (IndexError, TypeError):
                v = None
            row[str(key)] = "" if v is None else v
        rows.append(row)
    return rows


def _generic_to_rows(obj) -> list[dict]:
    """Bespoke payloads: find the longest list-of-dicts anywhere in the object."""
    best: list = []

    def walk(o):
        nonlocal best
        if isinstance(o, list) and o and all(isinstance(x, dict) for x in o):
            if len(o) > len(best):
                best = o
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return [{k: ("" if v is None else v) for k, v in r.items()} for r in best]


def _last_date(rows: list[dict]) -> str | None:
    for key in ("date", "month", "period", "Date", "Month"):
        vals = [str(r[key]) for r in rows if r.get(key)]
        if vals:
            return max(vals)
    return None


def run(dq: DQ, deadline=None) -> dict:
    out = {"files": [], "series": {}}
    for slug, (path, label, max_age) in SERIES.items():
        try:
            body = get(BASE.format(slug))
        except FetchError as e:
            dq.warn(NAME, f"{slug} ({label}) unavailable: {e}")
            continue
        archive_raw(f"rbihub/{slug}.json", body)
        try:
            obj = json.loads(body)
        except json.JSONDecodeError as e:
            dq.error(NAME, f"{slug}: invalid JSON ({e})")
            continue

        rows = _sdmx_to_rows(obj) if "dates" in obj and "values" in obj else _generic_to_rows(obj)
        if not rows:
            dq.error(NAME, f"{slug}: payload contained no tabular rows")
            continue
        if len(rows) < 30:
            dq.error(NAME, f"{slug}: only {len(rows)} rows — looks like a truncated "
                           f"stub, not a real series (this mirror has known stubs)")

        # Normalise field order across heterogeneous payloads.
        fields: list[str] = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
        rows = [{f: r.get(f, "") for f in fields} for r in rows]
        write_csv(path, rows, fields)
        out["files"].append("data/" + path)

        last = _last_date(rows)
        info = {"label": label, "n": len(rows), "last": last}
        out["series"][slug] = info
        if last and len(last) >= 7:
            try:
                y, m = int(last[:4]), int(last[5:7])
                age = (date.today() - date(y, m, 1)).days
                if age > max_age:
                    dq.warn(NAME, f"{slug} stale: last obs {last} ({age}d) — "
                                  f"mirror lag, patch the tail from another route")
            except ValueError:
                pass
        dq.note(NAME, f"{slug}: {len(rows)} rows, last {last}")

    if not out["series"]:
        raise FetchError("rbihub: no series retrieved")
    return out
