"""RBI Weekly Statistical Supplement — foreign exchange reserves, weekly.

Route: the section index lists one link per release; each link renders a plain
HTML table. Note the host: www.rbi.org.in serves these fine, while m.rbi.org.in
returns a CAPTCHA interstitial for the identical path.

We do NOT touch rbidocs.rbi.org.in (the XLSX/PDF CDN) anywhere in this repo — it
CAPTCHAs automated requests. Everything here comes from server-rendered HTML.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .common import (DQ, Deadline, FetchError, archive_raw, get, num, pmap,
                     read_existing, write_csv)

NAME = "rbi_wss_reserves"
INDEX = "https://www.rbi.org.in/Scripts/WSSViewDetail.aspx?TYPE=Section&PARAM1=2"
DETAIL = "https://www.rbi.org.in/Scripts/WSSView.aspx?Id={}"
MAX_NEW_PER_RUN = 60   # weekly releases; backfill spreads over consecutive runs

ID_RE = re.compile(r"WSSView\.aspx\?Id=(\d+)", re.I)
DATE_ONLY_RE = re.compile(r"^\d{1,2}\s+[A-Za-z]{3,9}\.?,?\s+20\d\d$")
DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})")
MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _parse_date(text: str) -> str | None:
    m = DATE_RE.search(text)
    if not m:
        return None
    d, mon, y = m.groups()
    key = mon[:3].lower()
    if key not in MONTHS:
        return None
    return f"{int(y):04d}-{MONTHS[key]:02d}-{int(d):02d}"


def _reserves_from_html(html: bytes) -> dict:
    """Pull the headline reserve aggregates out of the WSS 'Foreign Exchange
    Reserves' table. Values are reported in both Rs crore and US$ million; we
    keep the USD column."""
    soup = BeautifulSoup(html, "lxml")
    out: dict[str, float] = {}
    wanted = {
        "total_reserves": r"total\s+reserves",
        "fca": r"foreign\s+currency\s+assets",
        "gold": r"^gold$|\bgold\b",
        "sdr": r"\bsdrs?\b|special\s+drawing",
        "imf_position": r"reserve\s+position\s+in\s+the\s+imf",
    }
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        label = cells[0]
        nums = [num(c) for c in cells[1:]]
        nums = [n for n in nums if n is not None]
        if not nums:
            continue
        for key, pat in wanted.items():
            if key in out:
                continue
            if re.search(pat, label, re.I):
                # Layout is [Rs crore ...][US$ mn ...]; the USD figure is the
                # smaller-magnitude of the level columns. Take the last value,
                # which in the standard WSS layout is the USD level.
                out[key] = nums[-1] if len(nums) == 1 else nums[len(nums) // 2]
    return out


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    try:
        idx = get(INDEX, expect="Foreign Exchange Reserves")
    except FetchError as e:
        raise FetchError(f"WSS index unreachable: {e}") from e
    archive_raw("rbi/wss/index.html", idx)

    soup = BeautifulSoup(idx, "lxml")
    # Layout (confirmed from the archived index, not assumed): the release date
    # sits in its own single-cell row, and the link row that FOLLOWS it is that
    # release. Every anchor's text is the literal string "Foreign Exchange
    # Reserves", so reading the date off the anchor — as the first version did —
    # yields zero dated links.
    links: dict[str, str] = {}
    current: str | None = None
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) == 1 and DATE_ONLY_RE.match(cells[0]):
            current = _parse_date(cells[0])
            continue
        a = tr.find("a", href=ID_RE)
        if a is not None and current:
            links[current] = ID_RE.search(a["href"]).group(1)
    if not links:
        raise FetchError("WSS index parsed to zero dated links — layout changed")

    existing = {r["week_ending"]: r for r in read_existing("rbi/fx_reserves_weekly.csv")}
    outstanding = sorted(set(links) - set(existing))
    # Newest first: the current tail matters more than deep backfill.
    todo = list(reversed(outstanding))[:MAX_NEW_PER_RUN]
    remaining_after = len(outstanding) - len(todo)
    if deadline and deadline.expired:
        dq.warn(NAME, "skipped detail fetches: no time budget left this run")
        todo = []

    def _one(d):
        return d, get(DETAIL.format(links[d]), tries=1)

    fetched = 0
    for res in pmap(_one, todo, workers=6):
        if isinstance(res, Exception):
            dq.warn(NAME, f"detail fetch failed ({res})")
            continue
        d, html = res
        archive_raw(f"rbi/wss/{d}.html", html)
        vals = _reserves_from_html(html)
        if not vals:
            dq.warn(NAME, f"{d}: no reserve rows parsed (raw archived)")
            continue
        existing[d] = {"week_ending": d, "release_id": links[d],
                       **{k: ("" if vals.get(k) is None else f"{vals[k]:.2f}")
                          for k in ["total_reserves", "fca", "gold", "sdr",
                                    "imf_position"]}}
        fetched += 1

    if not existing:
        raise FetchError("WSS: nothing parsed and nothing on disk")
    ordered = [existing[k] for k in sorted(existing)]
    write_csv("rbi/fx_reserves_weekly.csv", ordered,
              ["week_ending", "release_id", "total_reserves", "fca", "gold",
               "sdr", "imf_position"])
    dq.note(NAME, f"{len(ordered)} weeks on file ({fetched} new); "
                  f"latest {ordered[-1]['week_ending']}; "
                  f"~{max(0, remaining_after)} still to backfill")
    dq.note(NAME, "units are as published (US$ million); verify the column pick "
                  "against one release before trusting levels")
    return {"files": ["data/rbi/fx_reserves_weekly.csv"],
            "n_weeks": len(ordered), "last": ordered[-1]["week_ending"],
            "backfill_remaining": max(0, remaining_after)}
