"""Global market and US macro series.

ARCHITECTURE NOTE — why this is not simply "the FRED module".

Runs 1 and 2 both failed here with every single series erroring. Run 2's improved
diagnostics showed the cause: not a block or a 403, but `Read timed out` on
fred.stlouisfed.org from the GitHub Actions runner. FRED is slow or throttled from
datacenter IPs, and with 30 series it consumed the entire time budget and returned
nothing.

The fix is not a longer timeout. It is to stop treating an unreliable host as a
hard dependency when a reliable one already covers most of the same data. The
`datasets/` GitHub mirrors are served from raw.githubusercontent.com — the same
CDN this repo lives on — and carry FRED's own H.10 numbers byte-for-byte.

So:
  TIER 1 (mirrors)   authoritative here, always attempted first, failure is an ERROR
  TIER 2 (FRED only) series no mirror carries; best effort, failure is a WARNING
                     and is reported as a coverage gap rather than killing the run

Between them the mirrors alone deliver USD/INR back to 1973 plus 21 other
crosses — which is the entire EM peer basket AND all six DXY constituents, so the
dollar index is reconstructible without FRED at all.
"""
from __future__ import annotations

import csv
import io
from datetime import date

from .common import (DQ, Deadline, FetchError, archive_raw, get,
                     guard_regression, num, pmap, write_csv)

NAME = "market"

RAW = "https://raw.githubusercontent.com/datasets/{}"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FRED_TXT = "https://fred.stlouisfed.org/data/{}.txt"

# ---------------------------------------------------------------- tier 1
FX_LONG = RAW.format("exchange-rates/main/data/daily.csv")

# The mirror labels rows by country name; map to currency codes.
# NOTE ON QUOTING, which matters for any return calculation: most are units of
# foreign currency PER USD, but Euro and United Kingdom are published inverted
# (USD per unit). Flagged in the output so downstream code cannot get it wrong.
# The mirror labels rows by country name; map to currency codes.
# QUOTING, verified against the raw file rather than assumed: EVERY cross is
# quoted as foreign currency per USD, including EUR (0.8635 on 2026-08-14, i.e.
# 1/1.158) and GBP (0.7377). An earlier version flagged EUR/GBP/AUD/NZD as
# USD-per-unit, which would have inverted any DXY reconstruction built on them.
FX_COUNTRIES = {
    "India": "INR", "China": "CNY", "Japan": "JPY", "South Korea": "KRW",
    "Taiwan": "TWD", "Singapore": "SGD", "Thailand": "THB", "Malaysia": "MYR",
    "Hong Kong": "HKD", "Brazil": "BRL", "Mexico": "MXN", "South Africa": "ZAR",
    "Canada": "CAD", "Sweden": "SEK", "Switzerland": "CHF", "Norway": "NOK",
    "Denmark": "DKK", "Australia": "AUD", "New Zealand": "NZD", "Euro": "EUR",
    "United Kingdom": "GBP",
}
QUOTE = "per_usd"

# url, output path, label, VALUE COLUMN NAME.
# The column name matters: the VIX mirror is DATE,OPEN,HIGH,LOW,CLOSE and a
# hardcoded column 1 silently published the OPEN as if it were the close
# (14.64 vs 14.25 on 2026-08-14) — wrong in every VIX-derived factor.
MIRRORS = {
    "brent_daily": (RAW.format("oil-prices/main/data/brent-daily.csv"),
                    "market/brent_daily.csv", "Brent crude, daily", None),
    "wti_daily": (RAW.format("oil-prices/main/data/wti-daily.csv"),
                  "market/wti_daily.csv", "WTI crude, daily", None),
    "vix_daily": (RAW.format("finance-vix/main/data/vix-daily.csv"),
                  "market/vix_daily.csv", "VIX close, daily", "CLOSE"),
    "gold_monthly": (RAW.format("gold-prices/main/data/monthly.csv"),
                     "market/gold_monthly.csv", "Gold USD/oz, monthly", None),
    "us_cpi_monthly": (RAW.format("cpi-us/main/data/cpiai.csv"),
                       "market/us_cpi_monthly.csv", "US CPI, monthly", None),
    "us_10y_monthly": (RAW.format("bond-yields-us-10y/main/data/monthly.csv"),
                       "market/us_10y_monthly.csv", "US 10y yield, monthly", None),
}

# ---------------------------------------------------------------- tier 2
FRED_ONLY = {
    "DGS10": "US 10y CMT, daily",
    "DGS2": "US 2y CMT, daily",
    "DFII10": "US 10y TIPS real, daily",
    "DFF": "Fed funds effective, daily",
    "DTWEXBGS": "Broad USD index, daily",
    "BAMLEMCBPIOAS": "EM corporate OAS, daily",
    "TRESEGINM052N": "India reserves excl gold, monthly (IMF IFS)",
    "RBINBIS": "BIS real broad EER, India, monthly",
}

# Without this the whole exercise is pointless, so its absence is fatal.
CRITICAL = "INR"


def _parse_series(body: bytes, col: str | None) -> list[dict]:
    """Mirror CSVs are <date>,<...>. `col` names the value column; None means the
    first one. Resolving by NAME rather than position is what stops an OHLC file
    from silently yielding the open."""
    rdr = csv.reader(io.StringIO(body.decode("utf-8", "replace")))
    header = next(rdr, None) or []
    idx = 1
    if col:
        want = col.strip().lower()
        matches = [i for i, h in enumerate(header) if h.strip().lower() == want]
        if not matches:
            raise FetchError(f"column {col!r} not in header {header}")
        idx = matches[0]
    rows = []
    for r in rdr:
        if len(r) <= idx:
            continue
        d, v = r[0].strip(), num(r[idx])
        if d and v is not None:
            rows.append({"date": d, "value": f"{v:g}"})
    if not rows:
        raise FetchError(f"parsed zero rows (header was {header})")
    rows.sort(key=lambda x: x["date"])
    return rows


def _fx(dq: DQ, out: dict) -> None:
    body = get(FX_LONG, tries=3)
    archive_raw("market/fx_daily_long.csv", body)
    per: dict[str, list[dict]] = {}
    rdr = csv.reader(io.StringIO(body.decode("utf-8", "replace")))
    next(rdr, None)
    for r in rdr:
        if len(r) < 3:
            continue
        d, country, val = r[0].strip(), r[1].strip(), num(r[2])
        code = FX_COUNTRIES.get(country)
        if not code or val is None:
            continue
        per.setdefault(code, []).append({"date": d, "value": f"{val:g}"})
    if CRITICAL not in per:
        raise FetchError(f"{CRITICAL} absent from the FX mirror — cannot proceed")
    missing = sorted(set(FX_COUNTRIES.values()) - set(per))
    if missing:
        # A renamed country key would otherwise drop a cross silently, leaving a
        # stale file in the repo that still looks current.
        dq.warn(NAME, f"FX mirror no longer carries: {', '.join(missing)}")
    for code, rows in sorted(per.items()):
        rows.sort(key=lambda x: x["date"])
        rel = f"market/fx_{code}.csv"
        if not guard_regression(dq, NAME, rel, rows):
            continue
        for r in rows:
            r["quote"] = QUOTE
        write_csv(rel, rows, ["date", "value", "quote"])
        out["series"][f"fx_{code}"] = {
            "label": f"{code} per USD", "n": len(rows),
            "first": rows[0]["date"], "last": rows[-1]["date"]}
    dq.note(NAME, f"FX mirror: {len(per)} currencies; "
                  f"{CRITICAL} {len(per[CRITICAL])} obs to {per[CRITICAL][-1]['date']}")
    _staleness(dq, f"fx_{CRITICAL}", per[CRITICAL][-1]["date"], 10, hard=True)


def _staleness(dq: DQ, name: str, last: str, limit_days: int, hard: bool = False):
    t = last[:10]
    if len(t) == 7:            # monthly series are dated YYYY-MM
        t += "-01"
    try:
        age = (date.today() - date.fromisoformat(t)).days
    except ValueError:
        dq.warn(NAME, f"{name}: unparseable last date {last!r} — not staleness-checked")
        return
    if age > limit_days:
        msg = f"{name} stale: last obs {last} is {age}d old (limit {limit_days}d)"
        # Weekends and holidays are normal; only a long gap is a real problem.
        (dq.error if hard and age > limit_days * 3 else dq.warn)(NAME, msg)


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    out: dict = {"files": [], "series": {}, "gaps": []}

    # ---- tier 1: mirrors. These are on the same CDN as this repo. ----
    # Guarded: the FX pull raising must not prevent the six independent mirrors
    # below from being attempted at all.
    try:
        _fx(dq, out)
    except Exception as e:  # noqa: BLE001
        dq.error(NAME, f"FX mirror failed: {e}")

    def _mirror(item):
        key, (url, path, label, col) = item
        if deadline and deadline.expired:
            raise FetchError("out of time budget")
        return key, path, label, col, get(url, tries=3)

    for res in pmap(_mirror, list(MIRRORS.items()), workers=4):
        if isinstance(res, Exception):
            dq.error(NAME, f"mirror fetch failed: {res}")
            continue
        key, path, label, col, body = res
        archive_raw(path, body)
        try:
            rows = _parse_series(body, col)
        except FetchError as e:
            dq.error(NAME, f"{key}: {e}")
            continue
        if not guard_regression(dq, NAME, path, rows):
            continue
        write_csv(path, rows, ["date", "value"])
        out["series"][key] = {"label": label, "n": len(rows),
                              "first": rows[0]["date"], "last": rows[-1]["date"]}
        _staleness(dq, key, rows[-1]["date"], 95 if "monthly" in key else 10)

    # ---- tier 2: FRED, best effort. ----
    # Generous timeout and low concurrency: the failure mode observed on the
    # runner is a slow read, not a refusal, and hammering it in parallel made it
    # worse. A miss here is a coverage gap, not a broken run.
    budget_left = deadline.remaining if deadline else 240
    if budget_left < 45:
        for sid, label in FRED_ONLY.items():
            out["gaps"].append(sid)
        dq.warn(NAME, f"skipped {len(FRED_ONLY)} FRED-only series: no time budget left")
        return _finish(dq, out)

    def _fred(sid):
        if deadline and deadline.expired:
            return sid, None, "out of time budget"
        errs = []
        for url in (FRED_CSV.format(sid), FRED_TXT.format(sid)):
            try:
                return sid, get(url, tries=1, timeout=45), None
            except Exception as e:  # noqa: BLE001
                errs.append(str(e)[:120])
        return sid, None, " | ".join(errs)

    for res in pmap(_fred, list(FRED_ONLY), workers=2):
        if isinstance(res, Exception):
            continue
        sid, body, err = res
        label = FRED_ONLY[sid]
        if body is None:
            out["gaps"].append(sid)
            dq.warn(NAME, f"{sid} ({label}) unavailable from FRED: {err}")
            continue
        archive_raw(f"fred/{sid}.csv", body)
        try:
            txt = body.decode("utf-8", "replace")
            rows = []
            for line in txt.splitlines()[1:]:
                parts = line.replace("\t", ",").split(",")
                if len(parts) < 2:
                    continue
                d, v = parts[0].strip(), parts[1].strip()
                if len(d) == 10 and v not in {".", ""}:
                    rows.append({"date": d, "value": v})
            if not rows:
                raise FetchError("zero rows")
            write_csv(f"fred/{sid}.csv", rows, ["date", "value"])
            out["series"][sid] = {"label": label, "n": len(rows),
                                  "first": rows[0]["date"], "last": rows[-1]["date"]}
        except Exception as e:  # noqa: BLE001
            out["gaps"].append(sid)
            dq.warn(NAME, f"{sid} parse failed: {e}")

    return _finish(dq, out)


def _finish(dq: DQ, out: dict) -> dict:
    # FRED-sourced series live under data/fred/, mirrors under data/market/.
    out["files"] = [(f"data/fred/{k}.csv" if k in FRED_ONLY else f"data/market/{k}.csv")
                    for k in out["series"]]
    if out["gaps"]:
        dq.warn(NAME, f"coverage gaps ({len(out['gaps'])}): {', '.join(out['gaps'])} — "
                      f"FRED-only series, no mirror exists; retried next run")
    dq.note(NAME, f"{len(out['series'])} series written, {len(out['gaps'])} gaps")
    return out
