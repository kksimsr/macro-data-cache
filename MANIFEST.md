# Data manifest

Last run: **2026-08-28T14:31:54+00:00** · 94.6s · 0 errors, 11 warnings

| source | status | detail |
|---|---|---|
| `rbi_forward_book` | ok | n_months=165, parsed=161, last=2026-06, backfill_remaining=0, seconds=9.5 |
| `rbi_wss` | ok | n_weeks=881, last=2026-08-21, backfill_remaining=0, seconds=6.1 |
| `rbihub` | ok | 4 series, seconds=1.9 |
| `nsdl_fpi` | ok | n=8, last=2026-08, backfill_remaining=19, seconds=22.9 |
| `india_misc` | ok | seconds=5.2 |
| `market` | ok | 27 series, seconds=43.7 |
| `india_external` | ok | n=3, seconds=1.9 |
| `official_rates` | ok | n=3, seconds=3.4 |

## Warnings

- *india_misc* — very few strikes carry open interest — post-Apr-2024 liquidity is thin; treat IV-derived factors with suspicion
- *market* — DGS10 (US 10y CMT, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- *market* — coverage gaps (8): DGS10, DGS2, DFII10, DFF, DTWEXBGS, BAMLEMCBPIOAS, TRESEGINM052N, RBINBIS — FRED-only series, no mirror exists; retried next run
- *rbi_forward_book* — 141 months given up on after 3 confirmed-absent probes: 2001-06, 2001-07, 2001-08, 2001-09, 2001-10, 2001-11, 2001-12, 2002-01...
- *rbihub* — sdmx-indices-of-reer-neer-monthly stale: last obs 2026-04-30 (149d) — mirror lag, patch the tail from another route
- *rbihub* — sdmx-forward-premia-inter-bank stale: last obs 2026-04-30 (149d) — mirror lag, patch the tail from another route
- *nsdl_fpi* — 2021: postback refused (ConnectionError) — historical backfill needs a browser; the current year is unaffected
- *nsdl_fpi* — 2022: postback refused (ConnectionError) — historical backfill needs a browser; the current year is unaffected
- *nsdl_fpi* — 2023: postback refused (ConnectionError) — historical backfill needs a browser; the current year is unaffected
- *nsdl_fpi* — 2024: postback refused (ConnectionError) — historical backfill needs a browser; the current year is unaffected
- *nsdl_fpi* — 2025: postback refused (ConnectionError) — historical backfill needs a browser; the current year is unaffected

## Coverage gaps

FRED-only series unavailable this run (no mirror exists); retried next run:

`DGS10`, `DGS2`, `DFII10`, `DFF`, `DTWEXBGS`, `BAMLEMCBPIOAS`, `TRESEGINM052N`, `RBINBIS`

## Market coverage

| id | label | n | first | last |
|---|---|---|---|---|
| `fx_AUD` | AUD per USD | 13945 | 1971-01-04 | 2026-08-21 |
| `fx_BRL` | BRL per USD | 7935 | 1995-01-02 | 2026-08-21 |
| `fx_CAD` | CAD per USD | 13958 | 1971-01-04 | 2026-08-21 |
| `fx_CHF` | CHF per USD | 13952 | 1971-01-04 | 2026-08-21 |
| `fx_CNY` | CNY per USD | 11392 | 1981-01-02 | 2026-08-21 |
| `fx_DKK` | DKK per USD | 13951 | 1971-01-04 | 2026-08-21 |
| `fx_EUR` | EUR per USD | 6931 | 1999-01-04 | 2026-08-21 |
| `fx_GBP` | GBP per USD | 13952 | 1971-01-04 | 2026-08-21 |
| `fx_HKD` | HKD per USD | 11452 | 1981-01-02 | 2026-08-21 |
| `fx_INR` | INR per USD | 13444 | 1973-01-02 | 2026-08-21 |
| `fx_JPY` | JPY per USD | 13946 | 1971-01-04 | 2026-08-21 |
| `fx_KRW` | KRW per USD | 11338 | 1981-04-13 | 2026-08-21 |
| `fx_MXN` | MXN per USD | 8220 | 1993-11-08 | 2026-08-21 |
| `fx_MYR` | MYR per USD | 13930 | 1971-01-04 | 2026-08-21 |
| `fx_NOK` | NOK per USD | 13951 | 1971-01-04 | 2026-08-21 |
| `fx_NZD` | NZD per USD | 13936 | 1971-01-04 | 2026-08-21 |
| `fx_SEK` | SEK per USD | 13951 | 1971-01-04 | 2026-08-21 |
| `fx_SGD` | SGD per USD | 11451 | 1981-01-02 | 2026-08-21 |
| `fx_THB` | THB per USD | 11371 | 1981-01-02 | 2026-08-21 |
| `fx_TWD` | TWD per USD | 10465 | 1983-10-03 | 2026-08-21 |
| `fx_ZAR` | ZAR per USD | 11695 | 1980-01-02 | 2026-08-21 |
| `brent_daily` | Brent crude, daily | 9963 | 1987-05-20 | 2026-08-25 |
| `wti_daily` | WTI crude, daily | 10231 | 1986-01-02 | 2026-08-25 |
| `vix_daily` | VIX close, daily | 9259 | 1990-01-02 | 2026-08-26 |
| `gold_monthly` | Gold USD/oz, monthly | 2323 | 1833-01 | 2026-07 |
| `us_cpi_monthly` | US CPI, monthly | 1361 | 1913-01-01 | 2026-06-01 |
| `us_10y_monthly` | US 10y yield, monthly | 879 | 1953-04-01 | 2026-06-01 |
