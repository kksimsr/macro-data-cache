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
  market/      FX crosses, oil, VIX, gold, US CPI (date,value[,quote])
  fred/        FRED-only series, one file per id (date,value)
  rbi/         forward book, weekly reserves, REER/NEER, forward premia, ECB
  india/       FPI flows, USD/INR option implied-vol log

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
| `market` | 21 FX crosses (incl. USD/INR from 1973), Brent, WTI, VIX close, gold, US CPI, US 10y — from GitHub mirrors; plus daily US yields, Fed funds, broad USD, EM OAS, India reserves and BIS REER from FRED | mirrors on `raw.githubusercontent.com`, then FRED | Mirrors are authoritative and their failure is an error; FRED is best-effort and its failure is a reported coverage gap. See below |
| `rbi_forward_book` | RBI net forward book from the IMF-format IRFCL reserve template, monthly from 2001 | `rbi.org.in` HTML | URL is constructible from the release date; we probe the last few weekdays of the month because Indian public holidays shift it |
| `rbi_wss` | Weekly foreign exchange reserves, in US$ mn | `www.rbi.org.in` HTML | Use the `www.` host — `m.rbi.org.in` serves a CAPTCHA. Rows are dated by `as_on`, not publication |
| `rbihub` | REER/NEER, forward premia, RBI spot intervention, ECB | `dbie.rbihub.in` JSON | **Backfill only** — see caveat below |
| `nsdl_fpi` | Monthly foreign portfolio flows, equity and debt | `fpi.nsdl.co.in` ASP.NET | Year selection is a postback; VIEWSTATE is replayed |
| `india_misc` | WPI files, NSE USD/INR option implied vol | mixed | IV is append-only, see below |

### Why FRED is not a hard dependency

FRED times out from GitHub Actions runners — not a block, a slow read — and with
thirty series it consumed an entire run and returned nothing, twice. The
`datasets/` mirrors carry FRED's own H.10 numbers on the same CDN this repo is
served from, and cover USD/INR plus twenty other crosses, oil, VIX, gold and US
CPI. Those twenty-one crosses are both the EM peer set and all six DXY
constituents, so the dollar index is reconstructible without FRED at all.

Mirrors are therefore tier 1 and their failure is an error. The handful of series
only FRED carries — daily US yields, Fed funds, the broad dollar index, EM credit
spreads, India reserves ex-gold, BIS REER — are tier 2: attempted with a generous
timeout and low concurrency, and if they fail they are listed as a coverage gap in
`MANIFEST.md` and retried next run rather than failing the job.

### Dating: `as_on` vs `published`

The WSS release published on 14 August reports reserves **as on 07 August**.
Dating rows by publication shifts the whole series forward by a week. Both are
stored, because the point of this cache is knowing what was knowable when.

### Repairing bad data without refetching

Modules that parse HTML stamp a `parser_version` on each row. When the parser is
fixed and the version bumped, stored rows below it are re-derived from the gzipped
payloads in `raw/` — no network, no refetch, no waiting for the source to serve
history again. This is the payoff of archiving raw first, and it exists because a
parser bug shipped once already and would otherwise have been frozen into the data
for ever, since a period already present in a CSV is never fetched again.

Writes are also guarded: a source is never allowed to replace a series with one
substantially shorter, because upstream mirrors are known to serve truncated
payloads and one bad response would otherwise wipe years of history.

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
python run.py --only market   # one source
python run.py                 # everything
```

`selftest.py` fixtures are reduced from real payloads archived in `raw/`, and the
expected values are the officially published figures (RBI net short forward book
50,586 for May-2026; reserves 707,002 for the 14 Aug release), so the suite checks
correctness rather than merely that the code runs. It also pins the specific bugs
that have shipped: reading a value off a label row instead of its maturity
sub-rows, accepting RBI's HTTP-200 "Error occured" page as data, picking a
variation column instead of the level, and treating a Unicode minus as a positive.

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
