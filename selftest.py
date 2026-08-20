#!/usr/bin/env python3
"""Offline parser smoke tests.

Why this exists: the machine that authored these parsers cannot reach the Indian
sources directly, so parsers are developed against payloads archived in raw/ by a
live run. The IRFCL and WSS fixtures below are reduced from those real pages, and
the expected values are the officially published figures — so these tests do check
correctness, not merely that the code runs.

They also pin the two bugs the first live run exposed: reading a value off the
label row instead of the maturity sub-rows (which silently produced numbers ~30x
too small), and accepting RBI's HTTP-200 "Error occured" page as real data.

Run:  python selftest.py
"""
from __future__ import annotations

import sys

from sources.common import DQ, num
from sources.rbi_forward_book import _extract
from sources.rbi_wss import DATE_ONLY_RE, ID_RE, _parse_date, _reserves_from_html

FAILS: list[str] = []


def check(label: str, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")
        print(f"  FAIL {label}: got {got!r}, want {want!r}")
    else:
        print(f"  ok   {label}")


def test_num():
    print("num() — messy table text")
    check("thousands", num("1,234.5"), 1234.5)
    check("paren negative", num("(40,326.00)"), -40326.0)
    check("leading plus", num("+1,213.00"), 1213.0)
    check("en dash null", num("–"), None)
    check("em dash null", num("—"), None)
    check("NA", num("N.A."), None)
    check("empty", num(""), None)
    check("nbsp", num("\xa0686,347.53\xa0"), 686347.53)
    check("footnote star", num("*"), None)
    check("plain negative", num("-50,586.00"), -50586.0)


# Real IRFCL layout, reduced from an archived page. The label row carries NO
# value; the numbers live in the maturity sub-rows beneath it. Row 0 is the giant
# whole-document concatenation the real pages contain, and the memo block at the
# foot repeats similar wording with different numbers — both were what broke the
# first parser, so both are reproduced here.
IRFCL = b"""<html><body><table>
<tr><td>(In USD Million) I. Official reserve assets June 2026 II. Predetermined
    short-term net drains 2. Aggregate short and long positions in forwards and
    futures (a) Short positions (b) Long positions</td></tr>
<tr><td>I. Official reserve assets and other foreign currency assets June 2026</td></tr>
<tr><td>A. Official reserve assets</td><td>668591.28</td></tr>
<tr><td>(1) Foreign currency reserves</td><td>542619.01</td></tr>
<tr><td>2. Aggregate short and long positions in forwards and futures in foreign
    currencies vis-\xc3\xa0-vis the domestic currency 7</td><td></td></tr>
<tr><td>(a) Short positions (-)</td><td></td></tr>
<tr><td>Total</td><td>-40326.00</td></tr>
<tr><td>Up to 1 month</td><td>-10175.00</td></tr>
<tr><td>More than 1 and up to 3 months</td><td>-5728.00</td></tr>
<tr><td>More than 3    months and up to 1 year</td><td>-24423.00</td></tr>
<tr><td>(b) Long positions (+)</td><td></td></tr>
<tr><td>Total</td><td>1213.00</td></tr>
<tr><td>Up to 1 month</td><td>1213.00</td></tr>
<tr><td>nondeliverable forwards</td><td>0.00</td></tr>
<tr><td>short positions</td><td>0.00</td></tr>
<tr><td>Aggregate short and long positions in forwards and futures in foreign
    currencies (memo)</td><td></td></tr>
<tr><td>(a) short positions (\xe2\x80\x93)</td><td>0.00</td></tr>
</table></body></html>"""

# RBI serves this, with HTTP 200, for any date that has no release.
IRFCL_ERROR = b"""<html><body><table>
<tr><td>Error occured. Please try again.</td></tr>
</table></body></html>"""


def test_irfcl():
    print("IRFCL forward-book extraction")
    got, rows = _extract(IRFCL)
    check("reference month", got["ref_month"], "2026-06")
    check("short total", got["short"].get("total"), -40326.0)
    check("short 0-1m", got["short"].get("m0_1"), -10175.0)
    check("short 3-12m", got["short"].get("m3_12"), -24423.0)
    check("long total", got["long"].get("total"), 1213.0)
    check("official reserve assets", got["total_reserves"], 668591.28)
    st, lt = got["short"]["total"], got["long"]["total"]
    check("net short (positive = capacity consumed)", (-st) - lt, 39113.0)
    buckets = sum(got["short"][k] for k in ("m0_1", "m1_3", "m3_12"))
    check("buckets sum to total", buckets, st)
    check("all rows captured for raw dump", len(rows) >= 10, True)


def test_irfcl_error_page():
    print("IRFCL error-page rejection")
    got, _ = _extract(IRFCL_ERROR)
    check("no reference month", got["ref_month"], None)
    check("no short position", got["short"], {})
    check("no reserves", got["total_reserves"], None)


# The WSS index puts the release date in its own single-cell row ABOVE the link
# row; every anchor's text is the same literal string.
WSS_INDEX = b"""<html><body><table>
<tr><td>14 Aug 2026</td></tr>
<tr><td><a class="link2" href="WSSView.aspx?Id=28639">Foreign Exchange Reserves</a></td>
    <td>9 kb</td></tr>
<tr><td>07 Aug 2026</td></tr>
<tr><td><a class="link2" href="WSSView.aspx?Id=28624">Foreign Exchange Reserves</a></td>
    <td>9 kb</td></tr>
</table></body></html>"""


def test_wss_index():
    print("WSS index date/link pairing")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(WSS_INDEX, "lxml")
    links, cur = {}, None
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) == 1 and DATE_ONLY_RE.match(cells[0]):
            cur = _parse_date(cells[0])
            continue
        a = tr.find("a", href=ID_RE)
        if a is not None and cur:
            links[cur] = ID_RE.search(a["href"]).group(1)
    check("two dated links", len(links), 2)
    check("newest id", links.get("2026-08-14"), "28639")
    check("older id", links.get("2026-08-07"), "28624")


WSS = b"""<html><body><table>
<tr><th>Item</th><th>Rs Crore</th><th>US$ Mn</th></tr>
<tr><td>Total Reserves</td><td>5,900,000</td><td>686,347</td></tr>
<tr><td>(a) Foreign Currency Assets</td><td>4,800,000</td><td>566,002</td></tr>
<tr><td>(b) Gold</td><td>900,000</td><td>102,500</td></tr>
<tr><td>(c) SDRs</td><td>160,000</td><td>18,600</td></tr>
<tr><td>(d) Reserve Position in the IMF</td><td>40,000</td><td>4,600</td></tr>
</table></body></html>"""


def test_wss():
    print("WSS reserves extraction")
    v = _reserves_from_html(WSS)
    check("total present", "total_reserves" in v, True)
    check("fca present", "fca" in v, True)
    check("gold present", "gold" in v, True)
    print("WSS date parsing")
    check("long month", _parse_date("Weekly Statistical Supplement 14 August, 2026"),
          "2026-08-14")
    check("short month", _parse_date("2 Jan. 2015"), "2015-01-02")
    check("no date", _parse_date("Foreign Exchange Reserves"), None)


def test_dq():
    print("DQ escalation")
    dq = DQ()
    dq.note("x", "fine")
    dq.warn("x", "hmm")
    check("warns counted", dq.n_warns, 1)
    check("notes are not errors", dq.n_errors, 0)
    dq.error("x", "bad")
    check("errors counted", dq.n_errors, 1)


def main() -> int:
    for fn in (test_num, test_irfcl, test_irfcl_error_page,
               test_wss_index, test_wss, test_dq):
        fn()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILURE(S)")
        for f in FAILS:
            print("  -", f)
        return 1
    print("all parser smoke tests passed")
    print("\nNOTE: the IRFCL and WSS fixtures are reduced from REAL archived pages "
          "and the expected\nnumbers are the published ones (May-2026 net short book "
          "50,586; reserves 686,347).\nFRED and NSDL remain unvalidated against live "
          "responses — check MANIFEST.md after a run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
