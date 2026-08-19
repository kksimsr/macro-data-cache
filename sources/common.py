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

TIMEOUT = 60


class FetchError(Exception):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get(url: str, *, tries: int = 3, backoff: float = 2.0, session=None,
        headers: dict | None = None, expect: str | None = None) -> bytes:
    """GET with retries. `expect` is a substring that must appear in the body;
    it is how we detect CAPTCHA interstitials and JS shells that return HTTP 200."""
    sess = session or requests
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    last = None
    for i in range(tries):
        try:
            r = sess.get(url, headers=h, timeout=TIMEOUT)
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
        except OSError:
            pass
    with gzip.open(p, "wb", compresslevel=9) as fh:
        fh.write(payload)
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


def append_snapshot(rel: str, rows: list[dict]) -> Path:
    """Append-only log, for series that exist only as live snapshots
    (NSE option implied vol). History here can only be accumulated forward,
    so never rewrite it."""
    existing = read_existing(rel)
    seen = {tuple(sorted(r.items())) for r in existing}
    fresh = [r for r in rows if tuple(sorted(r.items())) not in seen]
    if not fresh and existing:
        return DATA / rel
    combined = existing + fresh
    fields = list(combined[0].keys())
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


def num(s) -> float | None:
    """Parse a number out of messy table text. Handles thousands separators,
    parenthesised negatives, en/em dashes used as nulls, footnote markers."""
    if s is None:
        return None
    t = str(s).strip().replace(",", "").replace("\xa0", " ").strip()
    if t in {"", "-", "--", "–", "—", "N.A.", "NA", "n.a.", "*"}:
        return None
    neg = t.startswith("(") and t.endswith(")")
    if neg:
        t = t[1:-1]
    t = t.lstrip("+")
    keep = "".join(ch for ch in t if ch.isdigit() or ch in ".-")
    if keep in {"", "-", ".", "-."}:
        return None
    try:
        v = float(keep)
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
