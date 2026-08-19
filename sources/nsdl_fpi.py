"""NSDL FPI Monitor — net foreign portfolio flows, equity and debt.

Classic ASP.NET: the numbers are in the server-rendered HTML, but selecting a
different year is a postback, so we replay __VIEWSTATE / __EVENTVALIDATION to walk
the year dropdown back to 2002.

Flows matter here as the fast fuse: a current account deficit funded by FDI is
stable, one funded by portfolio money is a run risk. The debt split (general
limit / VRR / FAR) also isolates index-inclusion flows, which are a one-off level
shift rather than a trend and should not be read as sentiment.
"""
from __future__ import annotations

import re
from datetime import date

import requests
from bs4 import BeautifulSoup

from .common import DQ, FetchError, archive_raw, get, num, write_csv

NAME = "nsdl_fpi"
URL = "https://www.fpi.nsdl.co.in/web/Reports/Yearwise.aspx?RptType=6"
FIRST_YEAR = 2002


def _hidden(soup) -> dict:
    out = {}
    for inp in soup.find_all("input", type="hidden"):
        if inp.get("name"):
            out[inp["name"]] = inp.get("value", "")
    return out


def _year_select(soup):
    for sel in soup.find_all("select"):
        name = (sel.get("name") or "").lower()
        opts = [o.get("value", "") for o in sel.find_all("option")]
        if any(re.fullmatch(r"\d{4}", (o or "")) for o in opts) or "year" in name:
            return sel
    return None


def _rows_from(soup, year: int) -> list[dict]:
    out = []
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 3:
            continue
        label = cells[0]
        if not re.match(r"^[A-Za-z]{3,9}", label):
            continue
        mon = label[:3].title()
        if mon not in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]:
            continue
        nums = [num(c) for c in cells[1:]]
        if not any(n is not None for n in nums):
            continue
        rec = {"month": f"{year}-{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(mon)+1:02d}"}
        for i, n in enumerate(nums):
            rec[f"col{i+1}"] = "" if n is None else f"{n:.2f}"
        out.append(rec)
    return out


def run(dq: DQ) -> dict:
    sess = requests.Session()
    try:
        first = get(URL, session=sess, expect="html")
    except FetchError as e:
        raise FetchError(f"NSDL unreachable: {e}") from e
    archive_raw("nsdl/yearwise_default.html", first)
    soup = BeautifulSoup(first, "lxml")

    sel = _year_select(soup)
    years = []
    if sel:
        for o in sel.find_all("option"):
            v = (o.get("value") or o.get_text(strip=True) or "").strip()
            if re.fullmatch(r"\d{4}", v) and FIRST_YEAR <= int(v) <= date.today().year:
                years.append(v)
    if not years:
        dq.warn(NAME, "year dropdown not found — capturing default page only")
        years = [str(date.today().year)]

    all_rows: list[dict] = []
    header_note = None
    for y in years:
        if y == years[-1] or len(years) == 1:
            page, s = first, soup
        else:
            payload = _hidden(soup)
            payload[sel["name"]] = y
            payload["__EVENTTARGET"] = sel["name"]
            payload["__EVENTARGUMENT"] = ""
            try:
                r = sess.post(URL, data=payload, timeout=60,
                              headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    dq.warn(NAME, f"{y}: postback HTTP {r.status_code}")
                    continue
                page = r.content
            except Exception as e:  # noqa: BLE001
                dq.warn(NAME, f"{y}: postback failed ({e})")
                continue
            s = BeautifulSoup(page, "lxml")
        archive_raw(f"nsdl/yearwise_{y}.html", page)
        if header_note is None:
            heads = [th.get_text(" ", strip=True) for th in s.find_all("th")]
            header_note = " | ".join(heads[:12])
        rows = _rows_from(s, int(y))
        if not rows:
            dq.warn(NAME, f"{y}: no monthly rows parsed")
        all_rows.extend(rows)

    if not all_rows:
        raise FetchError("NSDL: no rows parsed from any year")
    fields = ["month"] + sorted({k for r in all_rows for k in r if k != "month"},
                                key=lambda x: int(x[3:]))
    all_rows = [{f: r.get(f, "") for f in fields} for r in all_rows]
    all_rows.sort(key=lambda r: r["month"])
    write_csv("india/fpi_flows_monthly.csv", all_rows, fields)
    dq.warn(NAME, f"columns are positional (col1..colN) — map them once against the "
                  f"live header before use. Header seen: {header_note}")
    dq.note(NAME, f"{len(all_rows)} months, {years[0]}..{years[-1]}, units Rs crore")
    return {"files": ["data/india/fpi_flows_monthly.csv"],
            "n": len(all_rows), "last": all_rows[-1]["month"]}
