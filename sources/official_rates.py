"""US Treasury par yields and ECB euro reference rates — two primary sources
that answer a plain GET with no key, no cookie and no bot gate.

WHY THIS REPLACED THE STOOQ MODULE. stooq.com now serves a JavaScript
proof-of-work challenge to datacentre IPs: the response is an HTML page asking
the client to hash a nonce until the digest starts with four zeros and POST the
answer back. Defeating a bot gate is not something this pipeline will do, so
the module was deleted rather than patched. Both sources here are the
publishers themselves, which is a better provenance than stooq ever was.

WHAT EACH ONE SOLVES

  US TREASURY   the daily par yield curve, every tenor, back to 1990. This is
                the source FRED's DGS10 and DGS2 are derived from, and FRED has
                been timing out from Actions for weeks. Straight to the well.

  ECB           daily reference rates for the euro against 30-odd currencies,
                back to 1999-01-04. Five of the six DXY constituents are in
                there, and the sixth is the dollar itself — which means the
                dollar index can be rebuilt a SECOND time, from a completely
                independent publisher, and the two rebuilds compared.

                That comparison is the point. The index was previously checked
                against four levels recalled from memory, which is a test that
                can pass for the wrong reason: the first reconstruction had two
                legs inverted and still matched at September 2022, because the
                euro was near parity and the two sign errors cancelled. Two
                independent datasets agreeing across 27 years cannot fail that
                way.

NOTE ON WHAT IS NOT HERE. The Indian 10-year government bond yield still has no
free source. The DBIE mirror carries 330 tables and none of them is a G-Sec
yield curve; every module so far has used the forward premium as the rate
differential instead, which by covered interest parity it is.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date

from .common import (DQ, Deadline, FetchError, archive_raw, get,
                     guard_regression, read_existing, write_csv)

NAME = "official_rates"

TREASURY = ("https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/daily-treasury-rates.csv/{y}/all"
            "?type=daily_treasury_yield_curve&field_tdr_date_value={y}"
            "&page&_format=csv")
TREASURY_FROM = 1990
# Treasury column -> output file. Resolved BY NAME: the VIX mirror once
# silently supplied OPEN where CLOSE was wanted and the fix was exactly this.
TREASURY_COLS = {"10 Yr": "market/us_10y_daily.csv",
                 "2 Yr": "market/us_2y_daily.csv"}

ECB = ("https://data-api.ecb.europa.eu/service/data/EXR/"
       "D.USD+JPY+GBP+CAD+SEK+CHF.EUR.SP00.A?format=csvdata&detail=dataonly")
ECB_FILE = "market/ecb_eur_reference_rates.csv"
ECB_CCY = ["USD", "JPY", "GBP", "CAD", "SEK", "CHF"]


# --- US Treasury -----------------------------------------------------------
def _treasury_year(y: int) -> dict[str, dict[str, str]]:
    """{column name: {iso date: value}} for one calendar year."""
    raw = get(TREASURY.format(y=y), tries=2, timeout=45)
    archive_raw(f"treasury/{y}.csv", raw)
    text = raw.decode("utf-8", "replace")
    if "Date" not in text.split("\n")[0]:
        raise FetchError(f"{y}: not a CSV payload ({text[:60]!r})")
    rd = csv.DictReader(io.StringIO(text))
    have = [c for c in TREASURY_COLS if c in (rd.fieldnames or [])]
    if not have:
        raise FetchError(f"{y}: none of {list(TREASURY_COLS)} in "
                         f"{rd.fieldnames}")
    out: dict[str, dict[str, str]] = {c: {} for c in have}
    for r in rd:
        m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", (r.get("Date") or "").strip())
        if not m:
            continue
        iso = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
        for c in have:
            v = (r.get(c) or "").strip()
            if not v or v in ("N/A", "-"):
                continue
            try:
                out[c][iso] = "%.6g" % float(v)
            except ValueError:
                continue
    return out


def _treasury(dq: DQ, deadline: Deadline | None) -> list[str]:
    """One request per calendar year. Years already on file are re-fetched only
    for the current and previous year — the rest never change."""
    this_year = date.today().year
    existing = {c: {r["date"]: r["value"] for r in read_existing(p)}
                for c, p in TREASURY_COLS.items()}
    have_years = {c: {d[:4] for d in v} for c, v in existing.items()}
    written = []

    todo = []
    for y in range(TREASURY_FROM, this_year + 1):
        stale = y >= this_year - 1
        missing = any(str(y) not in have_years[c] for c in TREASURY_COLS)
        if stale or missing:
            todo.append(y)
    todo.sort(reverse=True)          # newest first: a truncated run stays current
    dq.note(NAME, f"treasury: {len(todo)} year files to fetch")

    fetched = 0
    for y in todo:
        if deadline and deadline.expired:
            dq.warn(NAME, f"treasury: stopped after {fetched} years, "
                          f"{len(todo) - fetched} left for the next run")
            break
        try:
            got = _treasury_year(y)
        except FetchError as e:
            dq.warn(NAME, f"treasury {e}")
            continue
        for c, vals in got.items():
            existing[c].update(vals)
        fetched += 1

    for c, path in TREASURY_COLS.items():
        vals = existing[c]
        if len(vals) < 200:
            dq.warn(NAME, f"treasury {c}: only {len(vals)} rows — refusing to "
                          f"write a stub")
            continue
        rows = [{"date": d, "value": vals[d]} for d in sorted(vals)]
        if not guard_regression(dq, NAME, path, rows):
            continue
        write_csv(path, rows, ["date", "value"])
        written.append("data/" + path)
        dq.note(NAME, f"treasury {c}: {len(rows)} rows, {rows[0]['date']} to "
                      f"{rows[-1]['date']}, last {rows[-1]['value']}")
    return written


# --- ECB -------------------------------------------------------------------
def _ecb(dq: DQ) -> list[str]:
    raw = get(ECB, tries=2, timeout=90)
    archive_raw("ecb/eur_reference_rates.csv", raw)
    text = raw.decode("utf-8", "replace")
    rd = csv.DictReader(io.StringIO(text))
    need = {"CURRENCY", "TIME_PERIOD", "OBS_VALUE"}
    if not need.issubset(set(rd.fieldnames or [])):
        raise FetchError(f"ECB: expected {sorted(need)} in {rd.fieldnames}")
    by_date: dict[str, dict[str, str]] = {}
    for r in rd:
        c, d, v = r.get("CURRENCY"), r.get("TIME_PERIOD"), (r.get("OBS_VALUE") or "").strip()
        if c not in ECB_CCY or not d or not v:
            continue
        try:
            by_date.setdefault(d, {})[c] = "%.6g" % float(v)
        except ValueError:
            continue
    if len(by_date) < 2000:
        raise FetchError(f"ECB: only {len(by_date)} dates — expected ~7000")
    fields = ["date"] + ECB_CCY
    rows = [dict({"date": d}, **{c: by_date[d].get(c, "") for c in ECB_CCY})
            for d in sorted(by_date)]
    if not guard_regression(dq, NAME, ECB_FILE, rows):
        raise FetchError("ECB: refused as a regression against the file on disk")
    write_csv(ECB_FILE, rows, fields)
    dq.note(NAME, f"ECB reference rates: {len(rows)} days, {rows[0]['date']} "
                  f"to {rows[-1]['date']}, {len(ECB_CCY)} currencies")
    return ["data/" + ECB_FILE]


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    written, failed = [], []
    try:
        written += _ecb(dq)
    except FetchError as e:
        dq.warn(NAME, f"ECB unavailable: {e}")
        failed.append("ecb")
    if deadline and deadline.expired:
        dq.warn(NAME, "treasury: skipped, out of time budget")
        failed.append("treasury")
    else:
        try:
            written += _treasury(dq, deadline)
        except FetchError as e:
            dq.warn(NAME, f"treasury unavailable: {e}")
            failed.append("treasury")

    if not written:
        raise FetchError("official_rates: nothing retrieved — check the "
                         "archived payloads under raw/treasury/ and raw/ecb/")
    return {"files": written, "n": len(written), "failed": failed}
