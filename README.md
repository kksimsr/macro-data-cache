# macro-data-cache

A daily-refreshed cache of **public** macroeconomic and market time series, with a
focus on India and the global variables that drive the rupee. Everything here is
redistributed public data from official statistical agencies and central banks;
this repository adds fetching, parsing, normalisation and a point-in-time archive,
not new information.

The repository exists because the environment that consumes this data has heavily
restricted network egress and can only reach GitHub. GitHub Actions runners have
open egress, so the Action does the fetching and commits tidy CSVs that anything
can then read over `raw.githubusercontent.com`.

## Layout

```
data/          normalised CSVs — the output you actually consume
  fred/        one file per FRED series id (date,value)
  rbi/         forward book, weekly reserves, REER/NEER, forward premia, ECB
  india/       FPI flows, USD/INR option implied-vol log
  global/      gold
raw/           gzipped, unparsed source payloads, exactly as fetched
logs/          manifest.json — machine-readable run report
MANIFEST.md    human-readable run report: coverage, staleness, errors
sources/       one module per source
run.py         orchestrator
selftest.py    offline parser smoke tests
```

### Why `raw/` exists

Every payload is archived before any parsing is attempted. Several of these
sources are government HTML pages whose layout changes without notice, so a parser
break must never mean a lost fetch — parsers can be rewritten later against the
archived bytes without re-hitting the source. Payloads are gzipped and skipped when
byte-identical, so the archive stays small and git diffs stay meaningful.

### Point-in-time

Publication lags are large and uneven: quarterly balance-of-payments data arrives
about two months after the quarter ends, the RBI forward book about a month after
month-end, monthly price indices about two weeks. Any analysis that aligns a series
to its *reference* date rather than its *publication* date is using information
that did not exist at the time.

Git history is the vintage archive. Each commit is a dated snapshot of what was
actually knowable that day, so a correct as-of view is recoverable with
`git log`/`git show` rather than requiring a separate vintage database.

## Sources

| module | what | route | notes |
|---|---|---|---|
| `fred` | ~30 daily/monthly series: USD/INR, Brent, WTI, VIX, US yields, Fed funds, broad USD, US CPI, BIS real EER for India, India reserves ex-gold, nine EM crosses, six DXY constituents | `fredgraph.csv`, no key | Most reliable feed here |
| `rbi_forward_book` | RBI net forward book from the IMF-format IRFCL reserve template, monthly from 2001 | `rbi.org.in` HTML | URL is constructible from the release date; we probe the last few weekdays of the month because Indian public holidays shift it |
| `rbi_wss` | Weekly foreign exchange reserves | `www.rbi.org.in` HTML | Use the `www.` host — `m.rbi.org.in` serves a CAPTCHA for the same path |
| `rbihub` | REER/NEER, forward premia, RBI spot intervention, ECB | `dbie.rbihub.in` JSON | **Backfill only** — see caveat below |
| `nsdl_fpi` | Monthly foreign portfolio flows, equity and debt | `fpi.nsdl.co.in` ASP.NET | Year selection is a postback; VIEWSTATE is replayed |
| `india_misc` | WPI files, gold monthly, NSE USD/INR option implied vol | mixed | IV is append-only, see below |

### Known caveats, encoded in the code

- **`dbie.rbihub.in` is a mirror, not the source.** Run by an RBI subsidiary but
  self-described as pre-rendered from *scraped* DBIE data. Observed: multi-month
  staleness, at least one catalogue description mismatched to its payload, and at
  least one series truncated to a stub. Series pulled from here are stamped with
  their own last observation and flagged when stale. Do not treat as authoritative.
  The official `data.rbi.org.in/DBIE` is a JavaScript shell with no public API.
- **`rbidocs.rbi.org.in` is not used anywhere.** That host — which serves every RBI
  PDF and XLSX — returns a CAPTCHA interstitial to automated requests. Everything
  here comes from server-rendered HTML or JSON instead.
- **Option implied vol is append-only.** No historical IV file exists for USD/INR
  at any price. The NSE endpoint is a live snapshot, so history can only be
  accumulated forward and a missed day is a permanent gap.
- **Thin FX derivatives liquidity.** India's April 2024 mandatory-underlying-exposure
  rule sharply reduced exchange-traded FX volumes, and offshore NDF activity was
  further curtailed by rules effective 10 April 2026. Implied-vol and any
  onshore/offshore basis measures have a structural break and should be gated on
  open interest.
- **WPI base-year break.** The 2022-23 base series begins April 2023; the 2011-12
  base file is fetched alongside it so the two can be spliced.
- **Not included: CCIL.** CCIL publishes the most authoritative free INR NDF
  aggregates and daily G-sec yields, but its terms restrict commercial use of
  website data, so nothing from CCIL is fetched or redistributed here.
- **No free daily India 10-year yield exists.** CCIL restricts it, FBIL is a
  JavaScript app, and the usual aggregators cap history at a rolling window. The
  FRED series `INTGSBINM193N` has been frozen since 2017 and is not usable.

## Data quality is loud, never silent

A source that fails does not quietly vanish from the dataset. Failures and
staleness are recorded in `logs/manifest.json` and `MANIFEST.md`, and any error
makes the run exit non-zero so it surfaces in the Actions tab — while data that did
succeed is still committed. The alternative, a pipeline that silently emits a
shorter series, is how a backtest ends up quietly wrong.

`MANIFEST.md` is the first thing to read after any run.

## Running locally

```bash
pip install -r requirements.txt
python selftest.py            # offline parser smoke tests
python run.py --list          # available sources
python run.py --only fred     # one source
python run.py                 # everything
```

Note that the HTML parsers for the Indian sources were written against documented
page structure rather than live pages, and the synthetic fixtures in `selftest.py`
prove only that they run and handle messy numbers — not that they match reality.
The first live Actions run is the real test; read `MANIFEST.md` afterwards and
expect to adjust column mappings.

## Setup

1. Create the repository as **public**, so consumers can read
   `raw.githubusercontent.com` without a token.
2. **Settings → Actions → General → Workflow permissions → Read and write
   permissions.** Without this the Action runs but cannot commit its results.
3. **Actions → refresh → Run workflow** for the first pull. Expect the first run to
   take a while: it backfills roughly 300 months of the forward book and up to five
   years of weekly reserves, archiving each page.

The schedule is 02:30 UTC daily. Backfill is incremental — later runs only fetch
what is missing, plus a re-pull of the two most recent months of any series subject
to revision.

## Licence and attribution

Code: MIT. Data: belongs to the originating agencies — RBI, BIS via FRED, MOSPI,
the Office of the Economic Adviser, NSE, NSDL, EIA via FRED, and the Federal
Reserve. Consult each agency's own terms before redistributing or using
commercially.
