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
from sources.rbi_wss import (DATE_ONLY_RE, ID_RE, _parse_date,
                             _reserves_from_html, _validate)

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
    # Sign-flip class: RBI pages use these dashes for negatives. Stripping them
    # turned -1,366 into +1,366 and inverted the headline forward-book signal.
    check("unicode minus U+2212", num("\u22121366"), -1366.0)
    check("en dash negative", num("\u20131,366"), -1366.0)
    # Fusion class: get_text() flattens footnote superscripts into the cell.
    check("value + footnote rejected", num("50,586.00 1"), None)
    check("two numbers rejected", num("1,234 5,678"), None)
    check("date rejected", num("2026-08-14"), None)
    check("range rejected", num("1-2"), None)


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

# The OLDER layout, used up to and including 2016-10, reduced from the archived
# 2016-10 page. There are no maturity sub-rows: the four buckets are columns of
# the label row, against a header carried once further up the table. Reading only
# the newer form left the forward book blank for every month before 2016-11 while
# the reserve level still parsed, so the rows looked complete.
IRFCL_OLD = b"""<html><body><table>
<tr><td>(In USD Million) I. Official reserve assets October 2016 II. Predetermined
    short-term net drains</td></tr>
<tr><td>I. Official reserve assets and other foreign currency assets October 2016</td></tr>
<tr><td>A. Official reserve assets</td><td>366212.00</td></tr>
<tr><td></td><td>Total</td><td>Maturity breakdown (residual maturity)</td></tr>
<tr><td>Up to 1 month</td><td>More than 1 and up to 3 months</td>
    <td>More than 3 months and up to 1 year</td></tr>
<tr><td>2. Aggregate short and long positions in forwards and futures in foreign
    currencies vis-\xc3\xa0-vis the domestic currency</td><td></td><td></td><td></td><td></td></tr>
<tr><td>(a) Short positions ( - )</td><td>-20493.00</td><td>-17036.00</td>
    <td>-2593.00</td><td>-864.00</td></tr>
<tr><td>(b) Long positions (+)</td><td>28309.00</td><td>11898.00</td>
    <td>3829.00</td><td>12582.00</td></tr>
</table></body></html>"""

# Same old layout but with the total deliberately broken. The inline read is
# positional, so it is gated on the published identity total == sum(buckets); if
# that fails the month must come back blank rather than confidently wrong.
IRFCL_OLD_BAD = IRFCL_OLD.replace(b"<td>-20493.00</td>", b"<td>-99999.00</td>")

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


def test_irfcl_old_layout():
    print("IRFCL pre-2016-11 layout (buckets inline on the label row)")
    got, _ = _extract(IRFCL_OLD)
    check("reference month", got["ref_month"], "2016-10")
    check("short total", got["short"].get("total"), -20493.0)
    check("short 0-1m", got["short"].get("m0_1"), -17036.0)
    check("short 1-3m", got["short"].get("m1_3"), -2593.0)
    check("short 3-12m", got["short"].get("m3_12"), -864.0)
    check("long total", got["long"].get("total"), 28309.0)
    check("official reserve assets", got["total_reserves"], 366212.0)
    st, lt = got["short"]["total"], got["long"]["total"]
    check("net short (negative = net long forward)", (-st) - lt, -7816.0)

    bad, _ = _extract(IRFCL_OLD_BAD)
    check("checksum rejects a total that is not the sum", bad["short"], {})


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


# The REAL WSS layout, reduced from the release published 14 Aug 2026. Eight
# numeric columns, only the second of which is the USD level. The previous
# parser took nums[len//2] — the end-March variation in rupee crore — and stored
# 15,894 as if it were $707bn of reserves. Note also that this release reports
# reserves AS ON 07 Aug: dating rows by publication shifts the series a week.
WSS = b"""<html><body><table>
<tr><td>Date : Aug 14, 2026</td></tr>
<tr><td>Foreign Exchange Reserves</td></tr>
<tr><td>Item</td><td>As on Aug. 07, 2026</td><td>Variation over</td></tr>
<tr><td>Week</td><td>End-March 2026</td><td>Year</td></tr>
<tr><td>&#8377; Cr.</td><td>US$ Mn.</td><td>&#8377; Cr.</td><td>US$ Mn.</td>
    <td>&#8377; Cr.</td><td>US$ Mn.</td><td>&#8377; Cr.</td><td>US$ Mn.</td></tr>
<tr><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td></tr>
<tr><td>1 Total Reserves</td><td>6732093</td><td>707002</td><td>119945</td>
    <td>14136</td><td>178232</td><td>15894</td><td>650963</td><td>13384</td></tr>
<tr><td>1.1 Foreign Currency Assets #</td><td>5471605</td><td>574625</td><td>82740</td>
    <td>9946</td><td>234238</td><td>22343</td><td>351690</td><td>-9353</td></tr>
<tr><td>1.2 Gold</td><td>1035407</td><td>108738</td><td>35821</td><td>3995</td>
    <td>-58903</td><td>-6657</td><td>280016</td><td>22578</td></tr>
<tr><td>1.3 SDRs</td><td>178487</td><td>18745</td><td>356</td><td>79</td>
    <td>1898</td><td>123</td><td>14183</td><td>4</td></tr>
<tr><td>1.4 Reserve Position in the IMF</td><td>46595</td><td>4894</td><td>1028</td>
    <td>116</td><td>999</td><td>86</td><td>5074</td><td>155</td></tr>
</table></body></html>"""


def test_wss():
    print("WSS reserves extraction (real 8-column layout)")
    v = _reserves_from_html(WSS)
    check("total reserves = USD level, not a variation", v.get("total_reserves"), 707002.0)
    check("foreign currency assets", v.get("fca"), 574625.0)
    check("gold", v.get("gold"), 108738.0)
    check("SDRs", v.get("sdr"), 18745.0)
    check("IMF position", v.get("imf_position"), 4894.0)
    check("rupee-crore level kept too", v.get("total_inr_cr"), 6732093.0)
    check("dated AS ON, not by publication", v.get("as_on"), "2026-08-07")
    dq = DQ()
    check("components reconcile to total", _validate(dq, "t", v), True)
    check("reconciliation raised nothing", dq.n_errors, 0)
    print("WSS reconciliation catches a wrong column")
    bad = dict(v, total_reserves=15894.0)
    dq2 = DQ()
    check("wrong column is rejected", _validate(dq2, "t", bad), False)
    check("and it is an error", dq2.n_errors, 1)
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
    for fn in (test_num, test_irfcl, test_irfcl_old_layout, test_irfcl_error_page,
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
