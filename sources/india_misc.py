"""Three smaller India feeds that do not warrant a module each.

1. WPI  — eaindustry.nic.in serves static, predictably-named .xlsx. No JS, no key,
          no CAPTCHA. The easiest source in the whole register.
          Structural break: the 2022-23 base series only starts Apr-2023, so the
          2011-12 base file is pulled too and the two must be spliced downstream.
2. Gold — FRED removed all ICE Benchmark Administration data (incl. LBMA gold) in
          Jan 2022 with no replacement, so the monthly series comes from a GitHub
          mirror. Gold matters as an IMPORT BILL, not as a price: it is India's
          second largest import and gold-import surges have driven the current
          account before (notably 2011-13).
3. NSE  — USD/INR option chain, which exposes implied vol per strike. There is no
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
GOLD = ("https://raw.githubusercontent.com/datasets/gold-prices/main/data/monthly.csv")
NSE_HOME = "https://www.nseindia.com/"
NSE_OC = "https://www.nseindia.com/api/option-chain-currency?symbol=USDINR"


def _wpi(dq: DQ) -> list[str]:
    files = []
    today = date.today()
    got_new = False
    for back in range(0, 5):  # walk back a few months to find the latest published
        y, m = today.year, today.month - back
        while m <= 0:
            y, m = y - 1, m + 12
        tag = f"{y:04d}{m:02d}"
        try:
            body = get(WPI_NEW.format(tag), tries=1)
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
    # 2011-12 base, for the pre-Apr-2023 splice. Published with a longer lag.
    for back in range(1, 6):
        y, m = today.year, today.month - back
        while m <= 0:
            y, m = y - 1, m + 12
        tag = f"{y:04d}{m:02d}"
        try:
            body = get(WPI_OLD.format(tag), tries=1)
        except FetchError:
            continue
        archive_raw(f"wpi/monthly_index_{tag}.xls", body)
        files.append(f"raw/wpi/monthly_index_{tag}.xls.gz")
        dq.note(NAME, f"WPI (2011-12 base) latest file: {tag}")
        break
    return files


def _gold(dq: DQ) -> list[str]:
    body = get(GOLD)
    archive_raw("gold/monthly.csv", body)
    rows = []
    for line in body.decode("utf-8", "replace").splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        d, v = parts[0].strip(), num(parts[1])
        if d and v is not None:
            rows.append({"month": d[:7], "usd_per_oz": f"{v:.2f}"})
    if not rows:
        raise FetchError("gold: parsed zero rows")
    write_csv("global/gold_monthly.csv", rows, ["month", "usd_per_oz"])
    dq.note(NAME, f"gold: {len(rows)} months, last {rows[-1]['month']} "
                  f"= ${rows[-1]['usd_per_oz']}")
    return ["data/global/gold_monthly.csv"]


def _nse_iv(dq: DQ) -> list[str]:
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
    archive_raw(f"nse/option_chain_{date.today().isoformat()}.json", body)
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
    append_snapshot("india/usdinr_option_iv_log.csv", rows)
    live = sum(1 for r in rows if num(r["oi"]))
    dq.note(NAME, f"NSE IV: {len(rows)} strike-legs captured, {live} with open interest")
    if live < 10:
        dq.warn(NAME, "very few strikes carry open interest — post-Apr-2024 liquidity "
                      "is thin; treat IV-derived factors with suspicion")
    return ["data/india/usdinr_option_iv_log.csv"]


def run(dq: DQ, deadline=None) -> dict:
    files: list[str] = []
    errs = 0
    for label, fn in (("wpi", _wpi), ("gold", _gold), ("nse_iv", _nse_iv)):
        try:
            files += fn(dq)
        except Exception as e:  # noqa: BLE001
            errs += 1
            dq.error(NAME, f"{label} failed: {e}")
    if errs == 3:
        raise FetchError("india_misc: all three sub-feeds failed")
    return {"files": files}
