"""NSDL FPI Monitor — monthly net foreign portfolio flows, in INR crore.

Flows are the fast fuse: a current account deficit funded by FDI is stable, one
funded by portfolio money is a run risk. The debt split also isolates
index-inclusion flows (Debt-FAR), which are a one-off level shift rather than
sentiment and should not be read as a trend.

TABLE SHAPE, read off the archived page rather than guessed. Two header rows
stack a group header over sub-columns:

    group : Equity | Debt                              | Hybrid | Mutual Funds                                  | AIFs | Total
    sub   : Equity | Debt-General Limit, Debt-VRR, Debt-FAR | Hybrid | Equity, Debt, Hybrid, Solution Oriented, Other | AIF  |

giving 12 numeric columns per month. Verified: Jan-2026's eleven components sum
to -29,239 against the published total of -29,240.

POSTBACK. Year selection is an ASP.NET __doPostBack on the `ddl` dropdown. Runs 1
and 2 lost every historical year to `RemoteDisconnected`. Two causes, both fixed
here: the __VIEWSTATE was replayed from the *first* page for every subsequent
year (ASP.NET expects the token from the most recent response), and the server
drops reused keep-alive connections.
"""
from __future__ import annotations

import re
from datetime import date

import requests
from bs4 import BeautifulSoup

from .common import (DQ, Deadline, FetchError, archive_raw, get, num,
                     read_existing, write_csv)

NAME = "nsdl_fpi"
URL = "https://www.fpi.nsdl.co.in/web/Reports/Yearwise.aspx?RptType=6"
FIRST_YEAR = 2002
MAX_YEARS_PER_RUN = 5

# The page states the year it is showing: "Monthly FPI Net Investments
# (Calendar Year - 2026)". An ASP.NET postback that is ignored returns HTTP 200
# with the DEFAULT (current-year) table, so without checking this we would file
# 2026's twelve months under 2015 and mark 2015 permanently done.
YEAR_IN_PAGE_RE = re.compile(r"Calendar\s+Year\s*[-–]\s*(20\d\d)", re.I)

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# Fallback names, used only if the header rows cannot be read.
FALLBACK_COLS = ["equity", "debt_general_limit", "debt_vrr", "debt_far", "hybrid",
                 "mf_equity", "mf_debt", "mf_hybrid", "mf_solution_oriented",
                 "mf_other", "aif", "total"]


def _slug(s: str) -> str:
    s = re.sub(r"\(.*?\)", "", s).strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_") or "col"


def _hidden(soup) -> dict:
    return {i["name"]: i.get("value", "")
            for i in soup.find_all("input", type="hidden") if i.get("name")}


def _year_select(soup):
    for sel in soup.find_all("select"):
        if sel.get("name") and any(
                re.fullmatch(r"\d{4}", (o.get("value") or "").strip())
                for o in sel.find_all("option")):
            return sel
    return None


def _columns(rows: list[list[str]]) -> list[str]:
    """Build column names by pairing the group header with its sub-headers."""
    groups = subs = None
    for r in rows[:6]:
        if not groups and "Equity" in r and "Total" in r and len(r) <= 8:
            groups = r
        elif groups and subs is None and "Equity" in r and len(r) >= 8:
            subs = r
    if not subs:
        return list(FALLBACK_COLS)
    # The Mutual Funds block reuses Equity/Debt/Hybrid, so everything from the
    # SECOND "Equity" up to "AIF" is prefixed mf_. Detecting the block start this
    # way (rather than de-duplicating names as they collide) keeps the whole block
    # consistently prefixed, including Solution Oriented and Other.
    names, in_mf, seen_equity = [], False, False
    for raw in subs:
        key = _slug(raw)
        if key == "equity":
            if seen_equity:
                in_mf = True
            seen_equity = True
        elif key.startswith("aif") or key.startswith("alternative"):
            in_mf = False
        names.append(("mf_" + key) if in_mf else key)
    names.append("total")
    if len(set(names)) != len(names):
        return list(FALLBACK_COLS)
    return names


def _page_year(soup) -> int | None:
    m = YEAR_IN_PAGE_RE.search(soup.get_text(" ", strip=True))
    return int(m.group(1)) if m else None


def _rows_from(soup, year: int, dq: DQ) -> tuple[list[dict], list[str]]:
    for t in soup.find_all("table"):
        rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                for tr in t.find_all("tr")]
        rows = [r for r in rows if r]
        month_rows = [r for r in rows
                      if r and r[0].strip().title() in MONTHS and len(r) > 2]
        if not month_rows:
            continue
        cols = _columns(rows)
        width = max(len(r) - 1 for r in month_rows)
        if len(cols) != width:
            # Positional col1..colN used to be merged into the CSV, creating a
            # file with two disjoint schemas and marking the year permanently
            # done so a later parser fix could never repair it. Treat it as a
            # failure instead and leave the year outstanding.
            dq.warn(NAME, f"{year}: header gave {len(cols)} names for {width} data "
                          f"columns — skipping this year rather than storing "
                          f"unnamed columns")
            return [], []
        out = []
        for r in month_rows:
            m = MONTHS.index(r[0].strip().title()) + 1
            rec = {"month": f"{year}-{m:02d}"}
            vals = [num(c) for c in r[1:]]
            if not any(v is not None for v in vals):
                continue
            for i, name in enumerate(cols):
                v = vals[i] if i < len(vals) else None
                rec[name] = "" if v is None else f"{v:.2f}"
            out.append(rec)
        return out, cols
    return [], []


def _post(sess, payload, referer):
    r = sess.post(URL, data=payload, timeout=45, headers={
        "Referer": referer, "Origin": "https://www.fpi.nsdl.co.in",
        "Content-Type": "application/x-www-form-urlencoded",
        # The server drops reused keep-alive sockets, which surfaced as
        # RemoteDisconnected on every year after the first.
        "Connection": "close",
    })
    if r.status_code != 200:
        raise FetchError(f"HTTP {r.status_code}")
    return r.content


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    sess = requests.Session()
    try:
        first = get(URL, session=sess, expect="Yearwise")
    except FetchError as e:
        raise FetchError(f"NSDL unreachable: {e}") from e
    archive_raw("nsdl/yearwise_default.html", first)
    soup = BeautifulSoup(first, "lxml")

    sel = _year_select(soup)
    years = []
    if sel:
        for o in sel.find_all("option"):
            v = (o.get("value") or "").strip()
            if re.fullmatch(r"\d{4}", v) and FIRST_YEAR <= int(v) <= date.today().year:
                years.append(v)
    if not years:
        dq.warn(NAME, "year dropdown not found — capturing the default page only")
        years = [str(date.today().year)]

    prior = {r["month"]: r for r in read_existing("india/fpi_flows_monthly.csv")}
    cur = str(date.today().year)
    # A year counts as done only when it is COMPLETE. Keying on "any month
    # present" meant a truncated page permanently froze the other eleven months.
    counts: dict[str, int] = {}
    for k in prior:
        counts[k[:4]] = counts.get(k[:4], 0) + 1
    have = {y for y in counts if counts[y] >= 12}
    # Always refresh the current year; backfill the rest newest-first, a slice per run.
    todo = [y for y in reversed(years) if y not in have and y != cur][:MAX_YEARS_PER_RUN]
    todo = sorted(set(todo) | {cur})
    if deadline and deadline.expired:
        todo = [cur]
    remaining = len([y for y in years if y not in have and y != cur]) - \
        len([y for y in todo if y != cur])

    collected: list[dict] = []
    cols_seen: list[str] = []
    cur_soup = soup
    for y in todo:
        if y == cur:
            page, s = first, soup                 # the default view is the current year
            shown = _page_year(s)
            if shown is not None and shown != int(y):
                # In early January the default view may still show last year.
                dq.warn(NAME, f"default page shows {shown}, not {y} — filing it "
                              f"under {shown} rather than mislabelling")
                y = str(shown)
        elif deadline and deadline.expired:
            dq.warn(NAME, f"{y}: skipped, out of time budget")
            continue
        else:
            payload = _hidden(cur_soup)           # token from the LATEST response
            payload[sel["name"]] = y
            payload["__EVENTTARGET"] = sel["name"]
            payload["__EVENTARGUMENT"] = ""
            page = None
            for attempt in range(3):
                try:
                    page = _post(sess, payload, URL)
                    break
                except Exception as e:            # noqa: BLE001
                    if attempt == 2:
                        dq.warn(NAME, f"{y}: postback failed after 3 tries ({e})")
                    else:                         # rebuild the session and retry
                        sess = requests.Session()
                        try:
                            fresh = get(URL, session=sess, tries=1)
                            cur_soup = BeautifulSoup(fresh, "lxml")
                            payload = _hidden(cur_soup)
                            payload[sel["name"]] = y
                            payload["__EVENTTARGET"] = sel["name"]
                            payload["__EVENTARGUMENT"] = ""
                        except FetchError:
                            pass
            if page is None:
                continue
            s = BeautifulSoup(page, "lxml")
            cur_soup = s                          # carry the token forward
            shown = _page_year(s)
            if shown is not None and shown != int(y):
                dq.warn(NAME, f"{y}: postback returned the {shown} table — "
                              f"discarding rather than mislabelling")
                continue
        archive_raw(f"nsdl/yearwise_{y}.html", page)
        rows, cols = _rows_from(s, int(y), dq)
        if not rows:
            dq.warn(NAME, f"{y}: no monthly rows parsed (raw archived)")
            continue
        if cols and not cols_seen:
            cols_seen = cols
        collected.extend(rows)

    merged = dict(prior)
    for r in collected:
        merged[r["month"]] = r
    if not merged:
        raise FetchError("NSDL: nothing parsed and nothing on disk")

    # Field order is PINNED to the canonical list, not to whichever year happened
    # to be parsed first. Latching it from the loop meant a backfill run that
    # started at 2016 reshuffled the whole file's schema versus one that started
    # at 2021, rewriting every row and breaking positional consumers.
    fields = ["month"] + list(FALLBACK_COLS)
    for c in (cols_seen or []):
        if c not in fields:
            fields.append(c)
    for r in merged.values():
        for k in r:
            if k not in fields:
                fields.append(k)
    ordered = [{f: merged[m].get(f, "") for f in fields} for m in sorted(merged)]
    write_csv("india/fpi_flows_monthly.csv", ordered, fields)

    _reconcile(dq, ordered)
    dq.note(NAME, f"{len(ordered)} months on file (units: INR crore); "
                  f"~{max(0, remaining)} years still to backfill")
    return {"files": ["data/india/fpi_flows_monthly.csv"], "n": len(ordered),
            "last": ordered[-1]["month"], "backfill_remaining": max(0, remaining)}


def _reconcile(dq: DQ, rows: list[dict]) -> None:
    """The components must sum to the published total. If they stop doing so the
    column mapping has drifted, which would silently corrupt the flows factor."""
    if not rows or "total" not in rows[0]:
        return
    bad = 0
    checked = 0
    for r in rows[-24:]:
        tot = num(r.get("total"))
        parts = [num(v) for k, v in r.items()
                 if k not in {"month", "total"} and not k.startswith("col")]
        parts = [p for p in parts if p is not None]
        if tot is None or len(parts) < 5:
            continue
        checked += 1
        if abs(sum(parts) - tot) > max(2.0, abs(tot) * 0.01):
            bad += 1
    if checked and bad > checked * 0.2:
        dq.error(NAME, f"components fail to reconcile to the published total in "
                       f"{bad}/{checked} recent months — column mapping has drifted")
    elif checked:
        dq.note(NAME, f"column mapping reconciles in {checked - bad}/{checked} months")
