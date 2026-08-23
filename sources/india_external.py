"""India's external accounts from the DBIE mirror: monthly merchandise trade,
the published quarterly balance of payments, and monthly foreign investment
flows.

WHY THIS MODULE EXISTS. Three series were blocking real work:

  MONTHLY IMPORTS  the denominator of import cover. Without it there is no
                   cover series at all, however good the reserve data is.
  BoP OVERALL      the published quarterly balance. A monthly change in
                   reserves proxied it but still carried valuation effects
                   (gold, EUR/JPY translation) that RBI strips out.
  FPI HISTORY      NSDL refuses historical postbacks, so its flows file holds
                   the current year only — eight months, which is not enough
                   for an average to mean anything.

HOW THE SLUGS WERE FOUND, AND WHY THEY ARE NO LONGER GUESSED. Two earlier
versions of this file guessed. The first guessed the HOST as well and pointed
at `data.rbi.org.in/DBIE/api/...`, the empty JavaScript shell that rbihub.py's
docstring warns about; it could never have worked. The second used the right
host but invented slugs in the SDMX style and got one of four right by luck
(`foreign-trade`), then threw the payload away because it looked for a "date"
key in rows that use "month".

The mirror does publish a catalogue, just not as JSON: `/tables` is a
server-rendered page listing all ~330 datasets as `/section/slug` links. That
is what _catalogue() reads. The three slugs below were then confirmed against
the live mirror before this file was written — their exact payload shapes are
what the parsers expect, and each parser fails loudly rather than writing a
shape it does not recognise.

PROVENANCE. Same caveat as rbihub: a pre-rendered mirror of scraped DBIE data,
known to go stale and known to have served at least one truncated payload.
Backfill and history only, never a live signal.
"""
from __future__ import annotations

import json
import re

from .common import (DQ, Deadline, FetchError, archive_raw, get,
                     guard_regression, read_existing, write_csv)

NAME = "india_external"
BASE = "https://dbie.rbihub.in/data/{}.json"
CATALOGUE = "https://dbie.rbihub.in/tables"

MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def _catalogue(dq: DQ) -> set[str]:
    """Every dataset the mirror publishes. The /tables page is HTML, not JSON;
    the links on it are the slugs, and `/data/<slug>.json` is the payload."""
    try:
        raw = get(CATALOGUE, tries=2, timeout=45)
    except FetchError as e:
        dq.warn(NAME, f"catalogue page unreachable ({e}) — proceeding with the "
                      f"known slugs, which may since have been renamed")
        return set()
    archive_raw("india_external/tables.html", raw)
    slugs = set(re.findall(r'href="/[a-z0-9\-]+/([a-z0-9\-]+)"',
                           raw.decode("utf-8", "replace")))
    dq.note(NAME, f"catalogue lists {len(slugs)} datasets")
    return slugs


# --- date normalisation ----------------------------------------------------
def _month_iso(v: str) -> str:
    """'2026-01' and '2026:01(JAN)' both mean January 2026."""
    s = str(v).strip()
    m = re.match(r"^(\d{4})[-:](\d{1,2})", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    m = re.match(r"^(\d{4}).*?\(([A-Z]{3})\)", s.upper())
    if m and m.group(2) in MONTHS:
        return f"{int(m.group(1)):04d}-{MONTHS[m.group(2)]:02d}"
    return ""


def _fiscal_quarter_end(v: str) -> str:
    """'2025-26:Q3' is the Indian fiscal third quarter — October to December
    2025 — so it is dated to its last month, 2025-12. Getting this wrong by a
    quarter would silently misalign the balance of payments against every
    monthly series it is compared with."""
    m = re.match(r"^(\d{4})[-–]\d{2}:?\s*Q([1-4])", str(v).strip())
    if not m:
        return ""
    y, q = int(m.group(1)), int(m.group(2))
    return {1: f"{y}-06", 2: f"{y}-09", 3: f"{y}-12", 4: f"{y + 1}-03"}[q]


def _slug(text: str, n: int = 44) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return s[:n] or "unnamed"


# --- parsers ---------------------------------------------------------------
# Each returns (rows, key_fields). key_fields identify a row for merging, so a
# re-fetch updates a row in place instead of duplicating it.
def _trade(j: dict) -> tuple[list[dict], list[str]]:
    rows = []
    for r in j.get("data") or []:
        d = _month_iso(r.get("month", ""))
        if not d:
            continue
        out = {"date": d}
        out.update({k: ("" if v is None else v)
                    for k, v in r.items() if k != "month"})
        rows.append(out)
    if not rows or "imports_usd" not in rows[0]:
        raise FetchError(f"foreign trade: no imports_usd column in "
                         f"{list(rows[0]) if rows else 'an empty payload'}")
    return rows, ["date"]


def _bop(j: dict) -> tuple[list[dict], list[str]]:
    """Column-major-ish: 60 line items, and one record per (quarter, Credit /
    Debit / Net) holding all 60 values. Flattened to one row per quarter per
    type, with the item index kept in the column name so a relabelling upstream
    cannot silently move a column."""
    items = j.get("items") or []
    if len(items) < 10:
        raise FetchError(f"balance of payments: only {len(items)} line items")
    names = []
    for i, it in enumerate(items):
        # Nested quotes and line breaks inside an f-string need Python 3.12.
        # The workflow does not pin a version, so this stays plain.
        if isinstance(it, str):
            lab = it
        else:
            lab = (it or {}).get("label") or (it or {}).get("name") or str(i)
        names.append("i%02d_%s" % (i, _slug(lab)))
    rows = []
    for r in j.get("data") or []:
        d = _fiscal_quarter_end(r.get("period", ""))
        if not d:
            continue
        out = {"date": d, "fiscal_period": r.get("period", ""),
               "type": r.get("type", "")}
        vals = r.get("values") or []
        for i, nm in enumerate(names):
            v = vals[i] if i < len(vals) else None
            out[nm] = "" if v is None else v
        rows.append(out)
    if not rows:
        raise FetchError("balance of payments: no datable rows")
    if not names[0].startswith("i00_overall"):
        raise FetchError(f"balance of payments: item 0 is {names[0]!r}, "
                         f"expected the overall balance — the line-item order "
                         f"has changed and every column mapping is suspect")
    return rows, ["date", "type"]


def _fii(j: dict) -> tuple[list[dict], list[str]]:
    rows = []
    for r in j.get("data") or []:
        d = _month_iso(r.get("month", ""))
        if not d:
            continue
        out = {"date": d}
        out.update({k: ("" if v is None else v)
                    for k, v in r.items() if k != "month"})
        rows.append(out)
    if not rows or "fpis" not in rows[0]:
        raise FetchError(f"foreign investment: no fpis column in "
                         f"{list(rows[0]) if rows else 'an empty payload'}")
    return rows, ["date"]


# slug -> (output path, label, parser)
TARGETS = {
    "foreign-trade": ("india/trade_monthly.csv",
                      "monthly merchandise trade", _trade),
    "balance-of-payments-usd": ("india/bop_quarterly.csv",
                                "quarterly balance of payments, US$ mn", _bop),
    "foreign-investment-inflows-bulletin": (
        "india/fpi_monthly_rbi.csv",
        "monthly FDI and portfolio flows, US$ mn", _fii),
}


def _one(slug: str, path: str, label: str, parser, dq: DQ) -> dict:
    raw = get(BASE.format(slug), tries=2, timeout=45)
    archive_raw(f"india_external/{slug}.json", raw)
    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise FetchError(f"{label}: payload is not JSON ({e})") from e
    rows, keys = parser(doc)

    # Merge on the key fields rather than overwrite, so a truncated payload
    # cannot silently shorten the file.
    def k(r):
        return tuple(str(r.get(f, "")) for f in keys)

    prior = {k(r): r for r in read_existing(path)}
    for r in rows:
        prior[k(r)] = r
    merged = [prior[key] for key in sorted(prior)]
    if not guard_regression(dq, NAME, path, merged):
        raise FetchError(f"{label}: refused as a regression against the file "
                         f"already on disk")
    fields = ["date"] + sorted({f for r in merged for f in r} - {"date"})
    write_csv(path, [{f: r.get(f, "") for f in fields} for r in merged], fields)
    dq.note(NAME, f"{label}: {len(merged)} rows, {merged[0]['date']} to "
                  f"{merged[-1]['date']}")
    return {"rows": len(merged), "first": merged[0]["date"],
            "last": merged[-1]["date"], "file": "data/" + path}


def run(dq: DQ, deadline: Deadline | None = None) -> dict:
    known = _catalogue(dq)
    files, out, failed = [], {}, []

    for slug, (path, label, parser) in TARGETS.items():
        if deadline and deadline.expired:
            dq.warn(NAME, f"{label}: skipped, out of time budget")
            failed.append(slug)
            continue
        if known and slug not in known:
            dq.warn(NAME, f"{label}: '{slug}' is no longer in the catalogue — "
                          f"it may have been renamed. Trying it anyway; see "
                          f"raw/india_external/tables.html for the current "
                          f"list")
        # One bad payload must not cost the other two. The previous run lost
        # a working 430-row trade series because the source raised on the
        # first target and never reached the other two.
        try:
            info = _one(slug, path, label, parser, dq)
        except FetchError as e:
            dq.warn(NAME, f"{label}: {e}")
            failed.append(slug)
            continue
        except Exception as e:  # noqa: BLE001
            dq.warn(NAME, f"{label}: parser raised {type(e).__name__}: {e} — "
                          f"the payload is archived under raw/india_external/")
            failed.append(slug)
            continue
        files.append(info.pop("file"))
        out[slug] = info

    if not files:
        raise FetchError(
            f"india_external: all {len(TARGETS)} datasets failed ({failed}). "
            f"Every response is archived under raw/india_external/ — read "
            f"those, and raw/india_external/tables.html for the catalogue, "
            f"before changing slugs.")
    if failed:
        dq.warn(NAME, f"{len(failed)} of {len(TARGETS)} datasets failed: "
                      f"{failed}")
    out["files"] = files
    out["n"] = len(files)
    return out
