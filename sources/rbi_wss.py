"""RBI Weekly Statistical Supplement — foreign exchange reserves, weekly.

TABLE SHAPE (read off an archived page; every number below is from the release
published 14 Aug 2026):

    Item                    | As on Aug 07, 2026 | Variation over Week | ...End-March | ...Year
                            |  ₹ Cr.  | US$ Mn.  |  ₹ Cr.  | US$ Mn.   | ₹Cr | US$Mn | ₹Cr | US$Mn
    1   Total Reserves      | 6732093 |  707002  | 119945  |  14136    | ... |  ...  | ... |  ...
    1.1 Foreign Currency A. | 5471605 |  574625  |  82740  |   9946    | ... |  ...  | ... |  ...

Eight numeric columns, of which only column 2 is the USD level. The previous
version picked `nums[len(nums)//2]`, i.e. column 5 — the *end-March variation in
rupee crore* — and stored 15,894 as if it were reserves of $707bn. Worse, it
filtered out empty cells before indexing, so a row with a dash landed on a
different column than its neighbours. Columns are now anchored to the "US$ Mn."
header cell and empty cells are padded, never compacted.

DATING. The release published on 14 Aug reports reserves AS ON 07 Aug. Storing the
publication date as the observation date silently shifts the whole series forward
by a week — which matters, because the point of this dataset is point-in-time
correctness. Both dates are now recorded: `as_on` is the observation, `published`
is when it became knowable.

Host note: use www.rbi.org.in; m.rbi.org.in CAPTCHAs the identical path. This repo
never touches rbidocs.rbi.org.in, which CAPTCHAs all automated requests.
"""
from __future__ import annotations

import os
import re

from bs4 import BeautifulSoup

from .common import (DQ, Deadline, FetchError, archive_raw, get,
                     guard_regression, num, pmap, read_existing, read_raw,
                     write_csv)

NAME = "rbi_wss_reserves"
INDEX = "https://www.rbi.org.in/Scripts/WSSViewDetail.aspx?TYPE=Section&PARAM1=2"
DETAIL = "https://www.rbi.org.in/Scripts/WSSView.aspx?Id={}"
MAX_NEW_PER_RUN = 1500 if os.environ.get("DEEP", "").strip() not in ("", "0", "false", "False") else 60
MAX_ATTEMPTS = 4

# Bump when the parser changes: stored rows below this are re-derived from the
# archived HTML in raw/, with no refetch. This is what makes archive-first pay off
# — the previous parser's wrong values would otherwise persist forever, because a
# week already present in the CSV is never fetched again.
PARSER_VERSION = 2

ID_RE = re.compile(r"WSSView\.aspx\?Id=(\d+)", re.I)
DATE_ONLY_RE = re.compile(r"^\d{1,2}\s+[A-Za-z]{3,9}\.?,?\s+20\d\d$")
DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})")
AS_ON_RE = re.compile(r"As\s+on\s+([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})", re.I)
USD_HDR_RE = re.compile(r"^US\s*\$?\s*Mn", re.I)

MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

ITEMS = {
    "total_reserves": re.compile(r"^\d*\s*total\s+reserves", re.I),
    "fca": re.compile(r"foreign\s+currency\s+assets", re.I),
    "gold": re.compile(r"^\d[\d.]*\s*gold\b", re.I),
    "sdr": re.compile(r"\bsdrs?\b", re.I),
    "imf_position": re.compile(r"reserve\s+position\s+in\s+the\s+imf", re.I),
}
FIELDS = ["as_on", "published", "release_id", "total_reserves_usd_mn",
          "fca_usd_mn", "gold_usd_mn", "sdr_usd_mn", "imf_position_usd_mn",
          "total_reserves_inr_cr", "parser_version"]


def _parse_date(text: str) -> str | None:
    m = DATE_RE.search(text or "")
    if not m:
        return None
    d, mon, y = m.groups()
    key = mon[:3].lower()
    return f"{int(y):04d}-{MONTHS[key]:02d}-{int(d):02d}" if key in MONTHS else None


def _as_on(rows: list[list[str]]) -> str | None:
    for cells in rows[:12]:
        for c in cells:
            m = AS_ON_RE.search(c)
            if m:
                mon, d, y = m.groups()
                key = mon[:3].lower()
                if key in MONTHS:
                    return f"{int(y):04d}-{MONTHS[key]:02d}-{int(d):02d}"
    return None


def _reserves_from_html(html: bytes) -> dict:
    """Return the USD-million levels, anchored to the 'US$ Mn.' header column."""
    soup = BeautifulSoup(html, "lxml")
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True))
                     for c in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if not rows:
            continue
        # The unit row repeats "₹ Cr. | US$ Mn." across the level and variation
        # blocks; the FIRST US$ Mn. is the level column we want.
        usd_idx = None
        unit_width = 0
        for cells in rows:
            hits = [i for i, c in enumerate(cells) if USD_HDR_RE.match(c)]
            if len(hits) >= 2 and len(cells) >= 4:
                usd_idx, unit_width = hits[0], len(cells)
                break
        if usd_idx is None:
            continue
        out: dict = {"as_on": _as_on(rows)}
        found = 0
        for cells in rows:
            if len(cells) < usd_idx + 2:
                continue
            label = cells[0]
            # Pad rather than compact: dropping empty cells shifts the columns.
            vals = [num(c) for c in cells[1:]]
            # The unit row carries no label cell, the data rows do. If that ever
            # stops holding, the widths diverge and every value shifts a column —
            # and the additive check would NOT catch it, because the variation
            # columns reconcile among themselves just as the levels do.
            if len(vals) != unit_width:
                continue
            for key, pat in ITEMS.items():
                if key in out or not pat.search(label):
                    continue
                if usd_idx < len(vals):
                    out[key] = vals[usd_idx]
                    if key == "total_reserves" and vals:
                        out["total_inr_cr"] = vals[0]
                    found += 1
                break          # one label may only fill one field
        if found >= 3:
            return out
    return {}


def _validate(dq: DQ, tag: str, v: dict) -> bool:
    """Components must add up to the total. This is the check that would have
    caught the wrong-column bug on day one."""
    tot = v.get("total_reserves")
    parts = [v.get(k) for k in ("fca", "gold", "sdr", "imf_position")]
    if tot is None or any(p is None for p in parts):
        return True                        # not enough to judge; leave it
    s = sum(parts)
    if abs(s - tot) > max(50.0, abs(tot) * 0.005):
        dq.error(NAME, f"{tag}: components sum to {s:,.0f} but total is {tot:,.0f} "
                       f"— wrong column picked")
        return False
    return True


def _row(date_pub: str, rel_id: str, v: dict) -> dict:
    return {
        "as_on": v.get("as_on") or date_pub,
        "published": date_pub,
        "release_id": rel_id,
        "total_reserves_usd_mn": _f(v.get("total_reserves")),
        "fca_usd_mn": _f(v.get("fca")),
        "gold_usd_mn": _f(v.get("gold")),
        "sdr_usd_mn": _f(v.get("sdr")),
        "imf_position_usd_mn": _f(v.get("imf_position")),
        "total_reserves_inr_cr": _f(v.get("total_inr_cr")),
        "parser_version": str(PARSER_VERSION),
    }


def _f(v) -> str:
    return "" if v is None else f"{v:.2f}"


def _int(v, default: int = 0) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    try:
        idx = get(INDEX, expect="Foreign Exchange Reserves")
    except FetchError as e:
        raise FetchError(f"WSS index unreachable: {e}") from e
    archive_raw("rbi/wss/index.html", idx)

    soup = BeautifulSoup(idx, "lxml")
    # The release date is a single-cell row ABOVE the link row; every anchor's
    # text is the literal "Foreign Exchange Reserves", so the date is not in it.
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

    stored = {r["published"]: r for r in read_existing("rbi/fx_reserves_weekly.csv")
              if r.get("published")}
    misses = {r["published"]: _int(r.get("attempts"))
              for r in read_existing("rbi/_wss_misses.csv") if r.get("published")}

    # 1) Re-derive stale-parser rows from the archive. No network, no refetch.
    # Re-derive stale-parser rows from the archive. Rows are NEVER deleted here:
    # an earlier version dropped anything it could not re-parse, which (a) silently
    # shrank the series and (b) if no archive existed at all, emptied `stored`
    # entirely, tripped the regression guard, wrote nothing, and repeated forever.
    # A row that cannot be re-derived keeps its old value and its stale version, so
    # it is simply retried next time.
    redone = stale = 0
    for d, r in list(stored.items()):
        if _int(r.get("parser_version")) >= PARSER_VERSION:
            continue
        v = {}
        try:
            v = _reserves_from_html(read_raw(f"rbi/wss/{d}.html"))
        except Exception:  # noqa: BLE001
            pass
        if v and v.get("total_reserves") is not None and _validate(dq, d, v):
            stored[d] = _row(d, r.get("release_id", links.get(d, "")), v)
            redone += 1
        else:
            stale += 1
    if stale:
        dq.warn(NAME, f"{stale} rows still on parser v<{PARSER_VERSION} and could not "
                      f"be re-derived from raw/ — values retained, will retry")
    if redone:
        dq.note(NAME, f"re-derived {redone} weeks from archived HTML "
                      f"(parser v{PARSER_VERSION}) without refetching")

    # 2) Fetch what is missing, newest first, capped per run.
    outstanding = [d for d in sorted(links)
                   if d not in stored and misses.get(d, 0) < MAX_ATTEMPTS]
    todo = list(reversed(outstanding))[:MAX_NEW_PER_RUN]
    remaining_after = len(outstanding) - len(todo)
    if deadline and deadline.expired:
        dq.warn(NAME, "skipped detail fetches: no time budget left this run")
        todo = []

    def _one(d):
        if deadline and deadline.expired:
            return d, None
        return d, get(DETAIL.format(links[d]), tries=2)

    fetched = 0
    for res in pmap(_one, todo, workers=6):
        if isinstance(res, Exception):
            continue
        d, html = res
        if html is None:
            continue
        archive_raw(f"rbi/wss/{d}.html", html)
        v = _reserves_from_html(html)
        if not v or v.get("total_reserves") is None:
            misses[d] = misses.get(d, 0) + 1
            dq.warn(NAME, f"{d}: reserves table not parsed (raw archived, "
                          f"attempt {misses[d]}/{MAX_ATTEMPTS})")
            continue
        if not _validate(dq, d, v):
            misses[d] = misses.get(d, 0) + 1
            continue
        misses.pop(d, None)
        stored[d] = _row(d, links[d], v)
        fetched += 1

    if not stored:
        raise FetchError("WSS: nothing parsed and nothing on disk")
    ordered = [stored[k] for k in sorted(stored)]
    # Written before the guard, so attempt counters survive a blocked write.
    write_csv("rbi/_wss_misses.csv",
              [{"published": k, "attempts": v}
               for k, v in sorted(misses.items()) if k]
              or [{"published": "none", "attempts": "0"}], ["published", "attempts"])
    if not guard_regression(dq, NAME, "rbi/fx_reserves_weekly.csv", ordered):
        return {"files": [], "n_weeks": len(ordered), "last": ordered[-1]["as_on"]}
    write_csv("rbi/fx_reserves_weekly.csv", ordered, FIELDS)

    dq.note(NAME, f"{len(ordered)} weeks (units US$ mn, dated by as-on not "
                  f"publication); {fetched} new; ~{max(0, remaining_after)} to backfill")
    return {"files": ["data/rbi/fx_reserves_weekly.csv"], "n_weeks": len(ordered),
            "last": ordered[-1]["as_on"], "backfill_remaining": max(0, remaining_after)}
