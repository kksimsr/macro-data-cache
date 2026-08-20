"""Two smaller India feeds that do not warrant a module each.

Gold moved to sources/market.py (now at data/market/gold_monthly.csv with a
date,value schema, replacing data/global/gold_monthly.csv) so that exactly
one module owns each series.

1. WPI  — eaindustry.nic.in serves static, predictably-named .xlsx. No JS, no key,
          no CAPTCHA. The easiest source in the whole register.
          Structural break: the 2022-23 base series only starts Apr-2023, so the
          2011-12 base file is pulled too and the two must be spliced downstream.
2. NSE  — USD/INR option chain, which exposes implied vol per strike. There is no
          historical IV file anywhere, free or otherwise, so this is append-only:
          the history can only ever be accumulated forward from the day we start.
          Caveat: the Apr-2024 mandatory-underlying-exposure rule collapsed
          exchange-traded FX volumes, so gate any IV signal on open interest.
"""
from __future__ import annotations

import io
import json
from datetime import date, datetime, timezone

import requests

from .common import (DQ, FetchError, append_snapshot, archive_raw, get, num,
                     write_csv)

NAME = "india_misc"

WPI_NEW = "https://eaindustry.nic.in/indx_download_2223/wpi_monthly_index_{}.xlsx"
WPI_OLD = "https://eaindustry.nic.in/indx_download_1112/monthly_index_{}.xls"
NSE_HOME = "https://www.nseindia.com/"
NSE_OC = "https://www.nseindia.com/api/option-chain-currency?symbol=USDINR"


def _wpi(dq: DQ, deadline=None) -> list[str]:
    files = []
    today = date.today()
    got_new = False
    for back in range(0, 5):  # walk back a few months to find the latest published
        y, m = today.year, today.month - back
        while m <= 0:
            y, m = y - 1, m + 12
        tag = f"{y:04d}{m:02d}"
        if deadline and deadline.expired:
            break                 # 5 probes x 20s is uninterruptible otherwise
        try:
            body = get(WPI_NEW.format(tag), tries=1, timeout=12)
        except FetchError:
            continue
        archive_raw(f"wpi/wpi_monthly_index_{tag}.xlsx", body)
        dq.note(NAME, f"WPI (2022-23 base) latest file: {tag}")
        files.append(f"raw/wpi/wpi_monthly_index_{tag}.xlsx.gz")
        got_new = True
        break
    if not got_new:
        dq.warn(NAME, "WPI 2022-23 base file not found for any recent month "
                      "(site is known to be flaky — retry next run)")
    got_old = False
    # 2011-12 base, for the pre-Apr-2023 splice. Published with a longer lag.
    for back in range(1, 6):
        y, m = today.year, today.month - back
        while m <= 0:
            y, m = y - 1, m + 12
        tag = f"{y:04d}{m:02d}"
        if deadline and deadline.expired:
            break
        try:
            body = get(WPI_OLD.format(tag), tries=1, timeout=12)
        except FetchError:
            continue
        archive_raw(f"wpi/monthly_index_{tag}.xls", body)
        files.append(f"raw/wpi/monthly_index_{tag}.xls.gz")
        dq.note(NAME, f"WPI (2011-12 base) latest file: {tag}")
        got_old = True
        break
    if not got_old:
        # This series is discontinued, so a recent tag may simply not exist. Say
        # so rather than failing silently for ever.
        dq.warn(NAME, "WPI 2011-12 base (needed for the pre-Apr-2023 splice) not "
                      "found in the last 5 months — series may be discontinued")
    return files


def _nse_iv(dq: DQ, deadline=None) -> list[str]:
    sess = requests.Session()
    try:
        # NSE hands out a cookie on the homepage that the API then requires.
        sess.get(NSE_HOME, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        body = get(NSE_OC, session=sess, tries=2,
                   headers={"Referer": "https://www.nseindia.com/",
                            "Accept": "application/json"})
    except Exception as e:  # noqa: BLE001 - a flaky NSE must not fail the whole run
        dq.warn(NAME, f"NSE option chain unavailable this run ({e}) — "
                      f"IV history is append-only, a missed day is a permanent gap")
        return []
    # Fixed filename: a dated one added a permanent new blob every single
    # day. The CSV below is the history; this is just the latest payload.
    archive_raw("nse/option_chain_latest.json", body)
    try:
        obj = json.loads(body)
    except json.JSONDecodeError as e:
        dq.warn(NAME, f"NSE option chain: invalid JSON ({e})")
        return []
    recs = (obj.get("records") or {}).get("data") or []
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    underlying = (obj.get("records") or {}).get("underlyingValue")
    rows = []
    for r in recs:
        for side in ("CE", "PE"):
            leg = r.get(side)
            if not leg:
                continue
            rows.append({
                "capture_date": stamp[:10],
                "captured_utc": stamp,
                "expiry": str(r.get("expiryDate", "")),
                "strike": str(r.get("strikePrice", "")),
                "side": side,
                "iv": str(leg.get("impliedVolatility", "")),
                "oi": str(leg.get("openInterest", "")),
                "ltp": str(leg.get("lastPrice", "")),
                "underlying": str(underlying or ""),
            })
    if not rows:
        dq.warn(NAME, "NSE option chain returned no strikes")
        return []
    # Dedup on the observation, NOT the timestamp: the timestamp differs every
    # run, so a weekend re-run used to append a duplicate copy of Friday's chain.
    append_snapshot("india/usdinr_option_iv_log.csv", rows,
                    key=["capture_date", "expiry", "strike", "side"])
    live = sum(1 for r in rows if num(r["oi"]))
    dq.note(NAME, f"NSE IV: {len(rows)} strike-legs captured, {live} with open interest")
    if live < 10:
        dq.warn(NAME, "very few strikes carry open interest — post-Apr-2024 liquidity "
                      "is thin; treat IV-derived factors with suspicion")
    return ["data/india/usdinr_option_iv_log.csv"]


def run(dq: DQ, deadline=None) -> dict:
    files: list[str] = []
    errs = 0
    # NSE first: its history can only be accumulated forward, so if the budget
    # runs out it must not be the thing that gets dropped.
    # (gold moved to sources/market.py — one owner per series)
    for label, fn in (("nse_iv", _nse_iv), ("wpi", _wpi)):
        if deadline and deadline.expired and label != "nse_iv":
            dq.warn(NAME, f"{label}: skipped, out of time budget")
            continue
        try:
            files += fn(dq, deadline)
        except Exception as e:  # noqa: BLE001
            errs += 1
            dq.error(NAME, f"{label} failed: {e}")
    if not files:
        # Both sub-feeds downgrade their own failures to warnings, so without
        # this the module reported status=ok having written nothing at all —
        # exactly the silent disappearance the house rule forbids.
        raise FetchError("india_misc: no sub-feed produced any output")
    return {"files": files}
