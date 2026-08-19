#!/usr/bin/env python3
"""Offline parser smoke tests.

Why this exists: the machine that authored these parsers has no network access to
the Indian sources, so the HTML parsers below were written against documented page
structure rather than live pages. These fixtures cannot prove the parsers match
reality — only the first live run can do that — but they do prove the parsers run,
handle the messy-number cases, and fail loudly instead of silently emitting nulls.

Run:  python selftest.py
"""
from __future__ import annotations

import sys

from sources.common import DQ, num
from sources.rbi_forward_book import _extract
from sources.rbi_wss import _parse_date, _reserves_from_html

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


IRFCL = b"""<html><body><table>
<tr><td>I. Official reserve assets</td><td></td></tr>
<tr><td>Total official reserve assets</td><td>686,347.53</td></tr>
<tr><td>II. Predetermined short-term net drains</td><td></td></tr>
<tr><td>2. Aggregate short and long positions in forwards and futures</td>
    <td>Total</td><td>Up to 1 month</td></tr>
<tr><td>(a) Short positions ( - )</td><td>-40,326.00</td><td>-9,000.00</td></tr>
<tr><td>(b) Long positions ( + )</td><td>1,213.00</td><td>200.00</td></tr>
</table></body></html>"""


def test_irfcl():
    print("IRFCL forward-book extraction")
    got, rows = _extract(IRFCL)
    check("short", got["short_usd_mn"], -40326.0)
    check("long", got["long_usd_mn"], 1213.0)
    check("total reserves", got["total_reserves_usd_mn"], 686347.53)
    check("all rows captured", len(rows) >= 6, True)
    # the sign convention the pipeline writes out
    net = abs(got["short_usd_mn"]) - abs(got["long_usd_mn"])
    check("net short positive = capacity consumed", net, 39113.0)


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
    for fn in (test_num, test_irfcl, test_wss, test_dq):
        fn()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILURE(S)")
        for f in FAILS:
            print("  -", f)
        return 1
    print("all parser smoke tests passed")
    print("\nNOTE: fixtures are synthetic. The RBI/NSDL parsers are unvalidated "
          "against live pages until the first Actions run — check MANIFEST.md then.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
