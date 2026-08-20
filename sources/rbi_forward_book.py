"""RBI net forward book, from the IMF-format IRFCL reserve template.

For a managed float the spot rate is a censored signal — the RBI absorbs pressure
into reserves and, above all, into forwards. Gross reserves minus the net short
forward book is what actually measures remaining defensive capacity.

The URL is fully constructible, which is rare for RBI:
    https://rbi.org.in/scripts/Bs_sddsviewhtmldetails.aspx?pg=IMF<DDMMYYYY>.html
DDMMYYYY is the RELEASE date (normally the last working day of month M+1); the
reference date is end of month M. Indian public holidays shift the release day, so
we probe the last few weekdays and take the first page that validates.

PAGE STRUCTURE (learned from archived pages, not guessed).
The template is a flat sequence of rows where an item's LABEL sits on its own row
with an empty value, and the numbers follow underneath as separate maturity rows:

    ['2. Aggregate short and long positions in forwards and futures ...', '']
    ['(a) Short positions (-)', '']
    ['Total',                          '-40326.00']
    ['Up to 1 month',                  '-10175.00']
    ['More than 1 and up to 3 months',  '-5728.00']
    ['More than 3 months and up to 1 year', '-24423.00']
    ['(b) Long positions (+)', '']
    ['Total',                            '1213.00']
    ...

An earlier version read the value off the label row and silently latched onto a
memo line near the foot of the page, producing figures ~30x too small (-1,366
instead of -40,326 for May-2026). Hence: values are only ever read from the
maturity sub-rows, and the parsed total is sanity-checked below.

TWO VALIDATION TRAPS, both hit in the first live run:
1. RBI returns an HTTP 200 page reading "Error occured. Please try again." for
   dates with no release. It contains the site chrome — including the word
   "reserve" — so a naive content check passes and phantom months get recorded.
2. Probing a release date in the future silently yields that same error page.
Both are handled by requiring the page's own reference month to equal the month
we asked for.
"""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from .common import (DQ, PROBE_TIMEOUT, Deadline, FetchError, archive_raw, get,
                     last_working_days, month_end, month_iter, num, pmap,
                     read_existing, write_csv)

NAME = "rbi_forward_book"
URL = "https://rbi.org.in/scripts/Bs_sddsviewhtmldetails.aspx?pg=IMF{}.html"
START = date(2001, 6, 1)

MAX_NEW_PER_RUN = 36
MAX_PROBE_ATTEMPTS = 3
RECENT_MONTHS = 6

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
MONTH_RE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(20\d\d)\b")
# Anchored on the numbered item. The page's first row is a giant concatenation of
# the whole document (site nav), so an unanchored match lands on row 0 and the
# subsequent label search then runs past the wrong part of the table.
FWD_SECTION_RE = re.compile(r"^\d+\.\s*aggregate\s+short\s+and\s+long\s+positions"
                            r"\s+in\s+forwards?\s+and\s+futures", re.I)
SHORT_RE = re.compile(r"^\(?a\)?[\s.)]*short\s+positions?", re.I)
LONG_RE = re.compile(r"^\(?b\)?[\s.)]*long\s+positions?", re.I)
RESERVES_RE = re.compile(r"^A\.\s*Official\s+reserve\s+assets", re.I)
ERROR_RE = re.compile(r"error\s+occured|error\s+occurred", re.I)

BUCKETS = [
    ("total", re.compile(r"^total$", re.I)),
    ("m0_1", re.compile(r"^up\s+to\s+1\s+month$", re.I)),
    ("m1_3", re.compile(r"^more\s+than\s+1\s+and\s+up\s+to\s+3\s+months$", re.I)),
    ("m3_12", re.compile(r"^more\s+than\s+3\s+months?\s+and\s+up\s+to\s+1\s+year$", re.I)),
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _rows(html: bytes) -> list[list[str]]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tr in soup.find_all("tr"):
        cells = [_norm(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
        if cells:
            out.append(cells)
    return out


def _buckets_after(rows: list[list[str]], i: int) -> dict:
    """Read the maturity sub-rows that follow a label row."""
    got: dict[str, float | None] = {}
    for j in range(i + 1, min(i + 9, len(rows))):
        label = rows[j][0]
        key = next((k for k, rx in BUCKETS if rx.match(label)), None)
        if key is None:
            break                      # left the block
        if key in got:
            break                      # next item's block began
        got[key] = num(rows[j][1]) if len(rows[j]) > 1 else None
    return got


def _ref_month(rows: list[list[str]]) -> str | None:
    """The reference month is printed in the section-I heading."""
    for cells in rows[:12]:
        m = MONTH_RE.search(" ".join(cells))
        if m:
            return f"{int(m.group(2)):04d}-{MONTHS.index(m.group(1)) + 1:02d}"
    return None


def _extract(html: bytes) -> tuple[dict, list[list[str]]]:
    rows = _rows(html)
    got = {"ref_month": None, "short": {}, "long": {}, "total_reserves": None}
    if not rows:
        return got, rows
    if any(ERROR_RE.search(" ".join(r)) for r in rows[:5]):
        return got, rows                      # RBI's "Error occured" placeholder

    got["ref_month"] = _ref_month(rows)

    start = next((i for i, r in enumerate(rows) if FWD_SECTION_RE.search(r[0])), None)
    if start is not None:
        # Only look inside this section; the page repeats similar wording in a
        # memo block further down, which is what the first version latched onto.
        for j in range(start + 1, min(start + 16, len(rows))):
            label = rows[j][0]
            if not got["short"] and SHORT_RE.match(label):
                got["short"] = _buckets_after(rows, j)
            elif got["short"] and not got["long"] and LONG_RE.match(label):
                got["long"] = _buckets_after(rows, j)
                break
    for r in rows:
        if RESERVES_RE.match(r[0]) and len(r) > 1:
            got["total_reserves"] = num(r[1])
            break
    return got, rows


def _probe(ym: tuple[int, int]):
    """Fetch and validate the IRFCL page for reference month y-m."""
    y, m = ym
    ref = f"{y:04d}-{m:02d}"
    rel_month_end = month_end(y + (m // 12), (m % 12) + 1)
    today = date.today()
    for cand in last_working_days(rel_month_end, n=5):
        if cand > today:
            continue                    # release has not happened yet
        try:
            page = get(URL.format(cand.strftime("%d%m%Y")), tries=1,
                       timeout=PROBE_TIMEOUT)
        except FetchError:
            continue
        got, _ = _extract(page)
        if got["ref_month"] == ref:     # the only trustworthy check
            return ref, cand, page, got
    return ref, None, None, None


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    rows_on_file = {r["ref_month"]: r for r in read_existing("rbi/forward_book.csv")}
    # Drop rows written by the broken parser so they get refetched cleanly.
    rows_on_file = {k: v for k, v in rows_on_file.items() if v.get("short_total")}
    misses = {r["ref_month"]: int(r.get("attempts", 0))
              for r in read_existing("rbi/_irfcl_misses.csv")}

    today = date.today()
    targets = list(month_iter(START, month_end(today.year, today.month)))
    recent = {f"{y:04d}-{m:02d}" for y, m in targets[-RECENT_MONTHS:]}

    def wanted(y, m):
        ref = f"{y:04d}-{m:02d}"
        if ref in rows_on_file and ref not in recent:
            return False
        if misses.get(ref, 0) >= MAX_PROBE_ATTEMPTS and ref not in recent:
            return False
        return True

    outstanding = [(y, m) for y, m in targets if wanted(y, m)]
    todo = list(reversed(outstanding))[:MAX_NEW_PER_RUN]
    remaining_after = len(outstanding) - len(todo)

    if deadline and deadline.expired:
        dq.warn(NAME, "skipped: no time budget left this run")
        todo = []

    fetched = missed = 0
    for res in pmap(_probe, todo, workers=5):
        if isinstance(res, Exception):
            missed += 1
            continue
        ref, used, page, got = res
        if page is None:
            misses[ref] = misses.get(ref, 0) + 1
            missed += 1
            continue
        misses.pop(ref, None)
        archive_raw(f"rbi/irfcl/IMF_{ref}.html", page)

        s, l = got["short"], got["long"]
        st, lt = s.get("total"), l.get("total")
        if st is None:
            dq.warn(NAME, f"{ref}: short-position total not found (raw archived)")
        # Shorts are published negative, longs positive. Net short positive =
        # RBI owes dollars forward (capacity consumed); negative = net long.
        net = None if st is None else (-st) - (lt or 0.0)
        rows_on_file[ref] = {
            "ref_month": ref,
            "release_date": used.isoformat(),
            "short_total": "" if st is None else f"{st:.2f}",
            "short_0_1m": _f(s.get("m0_1")),
            "short_1_3m": _f(s.get("m1_3")),
            "short_3_12m": _f(s.get("m3_12")),
            "long_total": "" if lt is None else f"{lt:.2f}",
            # Positive = RBI is net short dollars forward, i.e. capacity consumed.
            "net_short_usd_mn": "" if net is None else f"{net:.2f}",
            "official_reserve_assets_usd_mn": _f(got["total_reserves"]),
        }
        fetched += 1

    if not rows_on_file:
        raise FetchError("forward book: nothing fetched and nothing on disk")

    ordered = [rows_on_file[k] for k in sorted(rows_on_file)]
    write_csv("rbi/forward_book.csv", ordered,
              ["ref_month", "release_date", "short_total", "short_0_1m",
               "short_1_3m", "short_3_12m", "long_total", "net_short_usd_mn",
               "official_reserve_assets_usd_mn"])
    if misses:
        write_csv("rbi/_irfcl_misses.csv",
                  [{"ref_month": k, "attempts": v} for k, v in sorted(misses.items())],
                  ["ref_month", "attempts"])

    parsed = sum(1 for r in ordered if r["net_short_usd_mn"])
    _sanity(dq, ordered)
    dq.note(NAME, f"{len(ordered)} months on file, {fetched} fetched, {missed} missed, "
                  f"{parsed} parsed, ~{max(0, remaining_after)} left to backfill")
    return {"files": ["data/rbi/forward_book.csv"], "n_months": len(ordered),
            "parsed": parsed, "backfill_remaining": max(0, remaining_after),
            "last": ordered[-1]["ref_month"]}


def _f(v) -> str:
    return "" if v is None else f"{v:.2f}"


def _sanity(dq: DQ, ordered: list[dict]) -> None:
    """Cross-check the parse. The buckets must sum to the total, and the recent
    book is known to run in the tens of billions — a total in the low thousands
    means we are reading the wrong cell again."""
    for r in ordered[-24:]:
        tot = num(r["short_total"])
        if tot is None:
            continue
        parts = [num(r[k]) for k in ("short_0_1m", "short_1_3m", "short_3_12m")]
        if all(p is not None for p in parts):
            s = sum(parts)
            if abs(s - tot) > max(1.0, abs(tot) * 0.005):
                dq.error(NAME, f"{r['ref_month']}: maturity buckets sum to {s:.0f} "
                               f"but total is {tot:.0f} — parser is misaligned")
    recent = [num(r["net_short_usd_mn"]) for r in ordered[-6:]
              if num(r["net_short_usd_mn"]) is not None]
    if recent and max(recent) < 5000:
        dq.error(NAME, f"recent net short book peaks at only {max(recent):.0f} USD mn; "
                       f"published figures are tens of billions — suspect wrong cell")
