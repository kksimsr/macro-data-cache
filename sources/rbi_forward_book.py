"""RBI net forward book, from the IMF-format IRFCL reserve template.

This is the single most valuable series in the indicator. For a managed float the
spot rate is a censored signal — the RBI absorbs pressure into reserves and, more
importantly, into forwards. Net reserves = gross reserves minus the net short
forward book is what actually measures remaining defensive capacity.

The URL is fully constructible, which is rare for RBI:
    https://rbi.org.in/scripts/Bs_sddsviewhtmldetails.aspx?pg=IMF<DDMMYYYY>.html
where DDMMYYYY is the RELEASE date (normally the last working day of month M+1)
and the reference date is end of month M. Indian public holidays shift the release
day, so we probe the last few weekdays of the month and take the first that parses.

Strategy: incremental (only fetch months absent from the CSV), archive every raw
page, and dump ALL table rows to a long CSV alongside the targeted extraction so a
parser miss never loses information.
"""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from .common import (DQ, FetchError, archive_raw, get, last_working_days,
                     month_end, month_iter, num, read_existing, write_csv)

NAME = "rbi_forward_book"
URL = "https://rbi.org.in/scripts/Bs_sddsviewhtmldetails.aspx?pg=IMF{}.html"
START = date(2001, 6, 1)  # first IRFCL release listed by RBI

SHORT_RE = re.compile(r"short\s+position", re.I)
LONG_RE = re.compile(r"long\s+position", re.I)
FWD_RE = re.compile(r"forwards?\s+and\s+futures", re.I)


def _tables(html: bytes):
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all("table"):
        rows = []
        for tr in t.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows:
            yield rows


def _extract(html: bytes) -> tuple[dict, list[list[str]]]:
    """Return (parsed fields, all rows) for one IRFCL page."""
    all_rows: list[list[str]] = []
    for rows in _tables(html):
        all_rows.extend(rows)

    got = {"short_usd_mn": None, "long_usd_mn": None, "total_reserves_usd_mn": None}
    in_fwd = False
    for cells in all_rows:
        label = cells[0] if cells else ""
        joined = " ".join(cells)
        is_header = bool(FWD_RE.search(joined))
        if is_header:
            in_fwd = True
        # Numbers are read from the data columns only; column 1 is the total.
        nums = [n for n in (num(c) for c in cells[1:]) if n is not None]

        # Match on the LABEL cell, never the whole row: the section header reads
        # "Aggregate short and long positions in forwards and futures", whose
        # trailing bucket captions ("Up to 1 month") otherwise parse as values.
        if not is_header and in_fwd and nums:
            if got["short_usd_mn"] is None and SHORT_RE.search(label):
                got["short_usd_mn"] = nums[0]
            elif got["long_usd_mn"] is None and LONG_RE.search(label):
                got["long_usd_mn"] = nums[0]
        if (got["total_reserves_usd_mn"] is None and nums
                and re.search(r"total\s+(official\s+)?reserve\s+assets", label, re.I)):
            got["total_reserves_usd_mn"] = nums[0]
    return got, all_rows


def run(dq: DQ) -> dict:
    existing = read_existing("rbi/forward_book.csv")
    have = {r["ref_month"] for r in existing}
    rows = {r["ref_month"]: r for r in existing}
    long_rows = []

    today = date.today()
    targets = [(y, m) for y, m in month_iter(START, month_end(today.year, today.month))]
    todo = [(y, m) for y, m in targets if f"{y:04d}-{m:02d}" not in have]
    # Always re-pull the two most recent months: RBI revises them.
    todo += [(y, m) for y, m in targets[-2:] if f"{y:04d}-{m:02d}" in have]

    fetched = failed = 0
    for y, m in todo:
        ref = f"{y:04d}-{m:02d}"
        rel_month_end = month_end(y + (m // 12), (m % 12) + 1)
        page = None
        used = None
        for cand in last_working_days(rel_month_end, n=6):
            tag = cand.strftime("%d%m%Y")
            try:
                page = get(URL.format(tag), tries=1, expect="reserve")
                used = cand
                break
            except FetchError:
                continue
        if page is None:
            # Months before the current release date legitimately do not exist yet.
            if rel_month_end <= today:
                failed += 1
                dq.warn(NAME, f"no IRFCL page found for ref {ref}")
            continue

        archive_raw(f"rbi/irfcl/IMF_{ref}.html", page)
        got, all_rows = _extract(page)
        for cells in all_rows:
            long_rows.append({"ref_month": ref, "cells": " | ".join(cells)})

        if got["short_usd_mn"] is None:
            dq.warn(NAME, f"{ref}: forward short position not parsed (raw archived)")
        short = got["short_usd_mn"]
        long_ = got["long_usd_mn"]
        net = None
        if short is not None:
            # RBI reports shorts as negative. Normalise: net_short_usd_mn positive
            # means the RBI is net short dollars forward, i.e. capacity consumed.
            net = abs(short) - (abs(long_) if long_ is not None else 0.0)
        rows[ref] = {
            "ref_month": ref,
            "release_date": used.isoformat(),
            "short_usd_mn": "" if short is None else f"{short:.2f}",
            "long_usd_mn": "" if long_ is None else f"{long_:.2f}",
            "net_short_usd_mn": "" if net is None else f"{net:.2f}",
            "total_reserves_usd_mn": ("" if got["total_reserves_usd_mn"] is None
                                      else f"{got['total_reserves_usd_mn']:.2f}"),
        }
        fetched += 1

    if not rows:
        raise FetchError("forward book: nothing fetched and nothing on disk")

    ordered = [rows[k] for k in sorted(rows)]
    write_csv("rbi/forward_book.csv", ordered,
              ["ref_month", "release_date", "short_usd_mn", "long_usd_mn",
               "net_short_usd_mn", "total_reserves_usd_mn"])
    if long_rows:
        prev = read_existing("rbi/irfcl_all_rows.csv")
        keep = [r for r in prev if r["ref_month"] not in {x["ref_month"] for x in long_rows}]
        write_csv("rbi/irfcl_all_rows.csv",
                  sorted(keep + long_rows, key=lambda r: r["ref_month"]),
                  ["ref_month", "cells"])

    parsed = sum(1 for r in ordered if r["net_short_usd_mn"])
    if parsed < 0.8 * len(ordered):
        dq.error(NAME, f"only {parsed}/{len(ordered)} months yielded a net forward "
                       f"position — parser needs work (raw HTML is archived)")
    dq.note(NAME, f"{len(ordered)} months on file, {fetched} fetched this run, "
                  f"{failed} unresolved, {parsed} parsed")
    return {"files": ["data/rbi/forward_book.csv"],
            "n_months": len(ordered), "parsed": parsed,
            "last": ordered[-1]["ref_month"]}
