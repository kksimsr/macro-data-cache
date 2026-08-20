"""Shared plumbing: HTTP with retries, raw archiving, atomic CSV writes, DQ flags.

Design rule for this repo: FETCH AND ARCHIVE RAW FIRST, PARSE SECOND.
Every scraped payload is gzipped into raw/ before any parsing is attempted, so a
broken parser is never a lost fetch — parsers can be rewritten offline against the
archived bytes without re-hitting the source.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = ROOT / "raw"
LOGS = ROOT / "logs"
for _d in (DATA, RAW, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

# Several Indian government sites reject default python-requests user agents.
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    "Accept-Language": "en-GB,en;q=0.9",
}

TIMEOUT = 20      # per-request; probing dead URLs must fail fast
PROBE_TIMEOUT = 10


class FetchError(Exception):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get(url: str, *, tries: int = 3, backoff: float = 2.0, session=None,
        headers: dict | None = None, expect: str | None = None,
        timeout: int | None = None) -> bytes:
    """GET with retries. `expect` is a substring that must appear in the body;
    it is how we detect CAPTCHA interstitials and JS shells that return HTTP 200."""
    sess = session or requests
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    last = None
    for i in range(tries):
        try:
            # (connect, read): a host that black-holes packets otherwise burns the
            # full read timeout just to establish nothing.
            r = sess.get(url, headers=h, timeout=(5, timeout or TIMEOUT))
            if r.status_code != 200:
                last = FetchError(f"HTTP {r.status_code} for {url}")
            else:
                body = r.content
                low = body[:4000].lower()
                if b"this question is for testing whether you are a human" in low:
                    last = FetchError(f"CAPTCHA interstitial served for {url}")
                elif expect and expect.encode().lower() not in body.lower():
                    last = FetchError(f"expected marker {expect!r} absent in {url}")
                else:
                    return body
        except Exception as e:  # noqa: BLE001 - want the message, whatever it is
            last = e
        if i < tries - 1:
            time.sleep(backoff * (i + 1))
    raise FetchError(str(last))


def archive_raw(name: str, payload: bytes) -> str:
    """Gzip a payload into raw/<name>.gz. Returns the sha256 of the raw bytes.
    Skips the write when content is byte-identical, to keep git history clean."""
    p = RAW / (name + ".gz")
    p.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(payload).hexdigest()
    if p.exists():
        try:
            with gzip.open(p, "rb") as fh:
                if hashlib.sha256(fh.read()).hexdigest() == digest:
                    return digest
        except Exception:  # noqa: BLE001
            # A truncated archive (run killed mid-write) raises EOFError, which
            # is NOT an OSError. Catching only OSError let that exception escape
            # and killed the source on every subsequent run, permanently.
            pass
    # Write via a temp file: the workflow can kill this process at any moment and
    # then commits whatever is on disk, so a partial .gz must never land.
    tmp = p.with_suffix(".gz.tmp")
    with gzip.open(tmp, "wb", compresslevel=9) as fh:
        fh.write(payload)
    os.replace(tmp, p)
    return digest


def read_raw(name: str) -> bytes:
    with gzip.open(RAW / (name + ".gz"), "rb") as fh:
        return fh.read()


def write_csv(rel: str, rows: list[dict], fieldnames: list[str] | None = None) -> Path:
    """Atomic, deterministic CSV write. Deterministic ordering matters: it keeps
    git diffs meaningful, which is what makes commit history usable as a
    point-in-time vintage archive."""
    if not rows:
        raise FetchError(f"refusing to write empty {rel}")
    fieldnames = fieldnames or list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    out = DATA / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8")
    tmp.replace(out)
    return out


def read_existing(rel: str) -> list[dict]:
    p = DATA / rel
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def append_snapshot(rel: str, rows: list[dict], key: list[str] | None = None) -> Path:
    """Append-only log for series that exist only as live snapshots (NSE option
    implied vol). History can only be accumulated forward, so never rewrite it.

    `key` names the columns that identify an observation. Without it the dedup
    key included the capture timestamp, which differs every run, so a weekend
    re-run appended a full duplicate copy of Friday's unchanged option chain.
    """
    existing = read_existing(rel)
    if not rows and not existing:
        raise FetchError(f"refusing to write empty {rel}")
    key = key or (list(rows[0].keys()) if rows else [])
    def _k(r):
        return tuple(str(r.get(k, "")) for k in key)
    seen = {_k(r) for r in existing}
    fresh = [r for r in rows if _k(r) not in seen]
    if not fresh:
        return DATA / rel
    combined = existing + fresh
    # Union of fields, so adding a column later does not raise.
    fields: list[str] = []
    for r in combined:
        for k in r:
            if k not in fields:
                fields.append(k)
    combined = [{f: r.get(f, "") for f in fields} for r in combined]
    return write_csv(rel, combined, fields)


def last_working_days(d: date, n: int = 5) -> list[date]:
    """The n most recent weekdays up to and including d, latest first.
    Used to hunt for RBI release dates: 'last working day of the month' shifts
    around Indian public holidays, which we do not model."""
    out, cur = [], d
    while len(out) < n:
        if cur.weekday() < 5:
            out.append(cur)
        cur -= timedelta(days=1)
    return out


def month_end(year: int, month: int) -> date:
    return date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)


def month_iter(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


NUM_TOKEN = re.compile(r"^[-+]?\d[\d,]*(?:\.\d+)?$")


def num(s) -> float | None:
    """Parse a number out of messy table text, or return None.

    Two failure modes found in adversarial review, both of which silently
    corrupted values rather than rejecting them:

    1. SIGN FLIP. The old filter kept only characters in ".-", so a Unicode
       minus (U+2212) or en-dash (U+2013) — both of which RBI pages use for
       negatives — was stripped and "\u22121366" parsed as +1366. On the forward
       book that inverts the headline signal: net short becomes net long.
    2. FUSION. get_text() flattens footnote superscripts into the cell, so
       "50,586.00 1" became 50586.001 and "1,234 5,678" became 12345678. Now a
       cell must contain exactly one numeric token or it is rejected.
    """
    if s is None:
        return None
    t = str(s).replace("\xa0", " ").strip()
    # Normalise dash variants to ASCII before any other handling.
    for dash in ("\u2212", "\u2013", "\u2014", "\u2010", "\u2011"):
        t = t.replace(dash, "-")
    if t in {"", "-", "--", "N.A.", "NA", "n.a.", "*", "..", "\u2026"}:
        return None
    neg = t.startswith("(") and t.endswith(")")
    if neg:
        t = t[1:-1].strip()
    # Exactly one token, or reject. Collapsing whitespace instead would turn
    # "50,586.00 1" (value + flattened footnote) into 50586.001.
    parts = t.split()
    if len(parts) != 1:
        return None
    t = parts[0]
    if not NUM_TOKEN.match(t):
        return None
    try:
        v = float(t.replace(",", ""))
    except ValueError:
        return None
    return -v if neg else v


class DQ:
    """Collects data-quality notes. The house rule on this project is that DQ
    problems are LOUD and never silent: anything recorded as an error here makes
    the whole run exit non-zero, even though good sources still get committed."""

    def __init__(self):
        self.entries: list[dict] = []

    def note(self, source: str, msg: str):
        self.entries.append({"level": "note", "source": source, "msg": msg})
        print(f"    note[{source}] {msg}", flush=True)

    def warn(self, source: str, msg: str):
        self.entries.append({"level": "warn", "source": source, "msg": msg})
        print(f"  ! WARN[{source}] {msg}", flush=True)

    def error(self, source: str, msg: str):
        self.entries.append({"level": "error", "source": source, "msg": msg})
        print(f"  !! ERROR[{source}] {msg}", flush=True)

    @property
    def n_errors(self) -> int:
        return sum(1 for e in self.entries if e["level"] == "error")

    @property
    def n_warns(self) -> int:
        return sum(1 for e in self.entries if e["level"] == "warn")


# --------------------------------------------------------------------------
# Run pacing.
#
# The first live run died on the job timeout with nothing committed, because the
# full backfill (~300 forward-book months, each needing several URL probes, plus
# years of weekly reserves) does not fit in one run. Two mechanisms fix that:
# a per-source Deadline, and a per-run cap on NEW items. Backfill then completes
# over consecutive daily runs instead of trying to finish in one.
# --------------------------------------------------------------------------

class Deadline:
    """Soft time budget. Sources check .expired and stop fetching, keeping
    whatever they already have rather than losing the run."""

    def __init__(self, seconds: float):
        self.seconds = seconds
        self.t0 = time.monotonic()

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    @property
    def remaining(self) -> float:
        return max(0.0, self.seconds - self.elapsed)

    @property
    def expired(self) -> bool:
        return self.remaining <= 0


def pmap(fn, items, workers: int = 6):
    """Thread-pooled map preserving input order. Exceptions are returned in
    place of results rather than raised, so one bad item cannot abort a batch."""
    from concurrent.futures import ThreadPoolExecutor
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as ex:
        futs = [ex.submit(fn, it) for it in items]
        out = []
        for f in futs:
            try:
                out.append(f.result())
            except Exception as e:  # noqa: BLE001
                out.append(e)
        return out


def guard_regression(dq: DQ, source: str, rel: str, new_rows: list,
                     tolerance: float = 0.9) -> bool:
    """Refuse to replace a series with a much shorter one.

    Upstream mirrors and the DBIE mirror are both known to serve truncated
    payloads. Without this, one bad response overwrites years of history with a
    stub and the only recovery is git archaeology. Returns True if it is safe to
    write."""
    prev = read_existing(rel)
    if prev and len(new_rows) < tolerance * len(prev):
        dq.error(source, f"{rel}: refusing to write {len(new_rows)} rows over "
                         f"{len(prev)} existing — upstream looks truncated")
        return False
    return True
