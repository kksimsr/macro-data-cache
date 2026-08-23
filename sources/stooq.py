"""stooq.com — free daily CSV for series that have no other reachable source.

WHY THIS EXISTS. Three gaps that nothing else in the pipeline fills:

  DXY        the dollar index. FRED is unreachable from Actions and the
             datasets/ mirrors do not carry it. The analysis currently REBUILDS
             DXY from its six constituents; that reconstruction is only
             validated against remembered levels, which is not good enough. A
             real series turns that into a proper check.
  US 10Y     daily. The datasets/ mirror is monthly only, and the FRED daily
             series sits behind the open circuit breaker.
  INDIA 10Y  the G-Sec yield. There has never been a free source for this in
             the pipeline; every module so far has worked around its absence by
             using the forward premium as the rate differential instead.

Stooq serves plain CSV over a GET with no key, no cookie and no JavaScript,
which is why it works from CI when almost nothing else Indian or FRED-shaped
does. It is a secondary source: treat it as a cross-check and a gap-filler, not
as a system of record.

FORMAT: Date,Open,High,Low,Close,Volume. Value columns are resolved BY NAME —
the VIX mirror once silently supplied OPEN where CLOSE was wanted, and the fix
was exactly this.
"""
from __future__ import annotations

import csv
import io

from .common import (DQ, Deadline, FetchError, archive_raw, get,
                     guard_regression, write_csv)

NAME = "stooq"
URL = "https://stooq.com/q/d/l/?s={}&i=d"

# symbol -> (output path, label, tolerated staleness in days)
SYMBOLS = {
    "^dxy": ("market/dxy_daily.csv", "US dollar index (ICE DXY)", 10),
    "10usy.b": ("market/us_10y_daily.csv", "US 10-year yield, daily", 10),
    "10inty.b": ("market/india_10y_daily.csv", "India 10-year G-Sec yield, daily", 10),
}


def _parse(raw: bytes, label: str) -> list[dict]:
    text = raw.decode("utf-8", "replace")
    # Stooq answers a bad symbol with a one-line body, not an HTTP error.
    if len(text) < 80 or "Date" not in text.split("\n")[0]:
        raise FetchError(f"{label}: not a CSV payload ({text[:60]!r})")
    rd = csv.DictReader(io.StringIO(text))
    if "Close" not in (rd.fieldnames or []):
        raise FetchError(f"{label}: no Close column in {rd.fieldnames}")
    out = []
    for r in rd:
        d, c = (r.get("Date") or "").strip(), (r.get("Close") or "").strip()
        if not d or not c or c == "-":
            continue
        try:
            v = float(c)
        except ValueError:
            continue
        out.append({"date": d, "value": f"{v:.6g}"})
    return out


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    written, gaps = [], []
    for sym, (path, label, stale_days) in SYMBOLS.items():
        if deadline and deadline.expired:
            dq.warn(NAME, f"{label}: skipped, out of time budget")
            continue
        try:
            raw = get(URL.format(sym), tries=2, timeout=45)
        except FetchError as e:
            dq.warn(NAME, f"{label} unavailable from stooq: {e}")
            gaps.append(sym)
            continue
        archive_raw(f"stooq/{sym.replace('^', '')}.csv", raw)
        try:
            rows = _parse(raw, label)
        except FetchError as e:
            dq.warn(NAME, str(e))
            gaps.append(sym)
            continue
        if len(rows) < 200:
            dq.warn(NAME, f"{label}: only {len(rows)} rows — refusing to write "
                          f"a stub over whatever is already there")
            gaps.append(sym)
            continue
        # Never replace a long series with a short one.
        if not guard_regression(dq, NAME, path, rows):
            continue
        write_csv(path, rows, ["date", "value"])
        written.append("data/" + path)
        dq.note(NAME, f"{label}: {len(rows)} rows, {rows[0]['date']} to "
                      f"{rows[-1]['date']}, last close {rows[-1]['value']}")

    if not written:
        raise FetchError("stooq: nothing retrieved — check the archived "
                         "payloads under raw/stooq/ before changing symbols")
    return {"files": written, "gaps": gaps, "n": len(written)}
