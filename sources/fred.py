"""FRED — the workhorse for global/US series and a few India ones.

No API key needed: fredgraph.csv is a public CSV endpoint. GitHub Actions runners
have unrestricted egress, so this works there even though it is unreachable from
the analysis sandbox (whose allowlist covers only package registries + GitHub).

Each series lands in data/fred/<ID>.csv as date,value.
"""
from __future__ import annotations

import csv
import io

from .common import DQ, Deadline, FetchError, archive_raw, get, pmap, write_csv

NAME = "fred"
BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"

# id -> (label, why it is here)
SERIES = {
    # --- core --------------------------------------------------------------
    "DEXINUS":      ("USD/INR spot, daily",              "core"),
    # --- global / US -------------------------------------------------------
    "DTWEXBGS":     ("Broad USD index, daily",           "global"),
    "DTWEXB":       ("Broad USD index (legacy, ends 2019-12)", "global, splice"),
    "DGS10":        ("US 10y CMT, daily",                "rates"),
    "DFII10":       ("US 10y TIPS real, daily",          "rates"),
    "DGS2":         ("US 2y CMT, daily",                 "global"),
    "DFF":          ("Fed funds effective, daily",       "rates"),
    "VIXCLS":       ("VIX close, daily",                 "risk"),
    "BAMLEMCBPIOAS":("EM corporate OAS, daily",          "risk"),
    "CPIAUCSL":     ("US CPI SA, monthly",               "prices"),
    # --- commodities -------------------------------------------------------
    "DCOILBRENTEU": ("Brent, daily",                     "commodity"),
    "DCOILWTICO":   ("WTI, daily",                       "commodity"),
    # --- India -----------------------------------------------------------
    "RBINBIS":      ("BIS real broad EER India, monthly","india"),
    "TRESEGINM052N":("India reserves excl gold, monthly","india (IMF IFS)"),
    "INDCPIALLMINMEI": ("India CPI (OECD) — STALE ~2025-03", "india, backfill only"),
    # --- EM crosses --------------------------------------------------------
    "DEXCHUS": ("CNY/USD", "em peer"),
    "DEXKOUS": ("KRW/USD", "em peer"),
    "DEXTAUS": ("TWD/USD", "em peer"),
    "DEXSIUS": ("SGD/USD", "em peer"),
    "DEXTHUS": ("THB/USD", "em peer"),
    "DEXMAUS": ("MYR/USD", "em peer"),
    "DEXBZUS": ("BRL/USD", "em peer"),
    "DEXMXUS": ("MXN/USD", "em peer"),
    "DEXSFUS": ("ZAR/USD", "em peer"),
    # --- DXY constituents ---------------------------------------------------
    "DEXUSEU": ("USD/EUR", "DXY 57.6%"),
    "DEXJPUS": ("JPY/USD", "DXY 13.6%"),
    "DEXUSUK": ("USD/GBP", "DXY 11.9%"),
    "DEXCAUS": ("CAD/USD", "DXY 9.1%"),
    "DEXSDUS": ("SEK/USD", "DXY 4.2%"),
    "DEXSZUS": ("CHF/USD", "DXY 3.6%"),
}

# Series known to be dead upstream. Absence of fresh data is expected, not an error.
FROZEN = {"DTWEXB", "INDCPIALLMINMEI"}


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    out = {"files": [], "series": {}}
    ids = list(SERIES)

    def _fetch(sid):
        return sid, get(BASE.format(sid))

    fetched = dict()
    for res in pmap(_fetch, ids, workers=6):
        if isinstance(res, Exception):
            continue
        fetched[res[0]] = res[1]
    for sid in ids:
        label, _why = SERIES[sid]
        body = fetched.get(sid)
        if body is None:
            dq.error(NAME, f"{sid} ({label}) fetch failed")
            continue
        archive_raw(f"fred/{sid}.csv", body)
        try:
            rdr = csv.reader(io.StringIO(body.decode("utf-8", "replace")))
            header = next(rdr)
            rows = []
            for r in rdr:
                if len(r) < 2:
                    continue
                d, v = r[0].strip(), r[1].strip()
                if not d or v in {".", ""}:
                    continue  # FRED encodes missing observations as "."
                rows.append({"date": d, "value": v})
            if not rows:
                dq.error(NAME, f"{sid} parsed to zero rows (header was {header})")
                continue
            write_csv(f"fred/{sid}.csv", rows, ["date", "value"])
            out["files"].append(f"data/fred/{sid}.csv")
            out["series"][sid] = {
                "label": label, "n": len(rows),
                "first": rows[0]["date"], "last": rows[-1]["date"],
            }
            if sid not in FROZEN:
                # Daily series should be within ~10d; monthly within ~75d.
                from datetime import date as _date
                age = (_date.today() - _date.fromisoformat(rows[-1]["date"])).days
                limit = 75 if sid in {"CPIAUCSL", "RBINBIS", "TRESEGINM052N"} else 12
                if age > limit:
                    dq.warn(NAME, f"{sid} stale: last obs {rows[-1]['date']} ({age}d old)")
        except Exception as e:  # noqa: BLE001
            dq.error(NAME, f"{sid} parse failed: {e}")
    if not out["series"]:
        raise FetchError("FRED returned nothing at all — likely a network/egress problem")
    dq.note(NAME, f"{len(out['series'])}/{len(SERIES)} series written")
    return out
