# Data manifest

Last run: **2026-09-21T08:09:30+00:00** · 111.5s · 0 errors, 10 warnings

| source | status | detail |
|---|---|---|
| `rbi_forward_book` | ok | n_months=166, parsed=162, last=2026-07, backfill_remaining=0, seconds=5.3 |
| `rbi_wss` | ok | n_weeks=884, last=2026-09-11, backfill_remaining=0, seconds=16.2 |
| `rbihub` | ok | 4 series, seconds=1.8 |
| `nsdl_fpi` | ok | n=8, last=2026-08, backfill_remaining=19, seconds=29.5 |
| `india_misc` | ok | seconds=10.1 |
| `market` | ok | 27 series, seconds=43.1 |
| `india_external` | ok | n=3, seconds=1.9 |
| `official_rates` | ok | n=3, seconds=3.6 |

## Warnings

- *market* — DGS10 (US 10y CMT, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- *market* — coverage gaps (8): DGS10, DGS2, DFII10, DFF, DTWEXBGS, BAMLEMCBPIOAS, TRESEGINM052N, RBINBIS — FRED-only series, no mirror exists; retried next run
- *rbi_forward_book* — 140 months given up on after 3 confirmed-absent probes: 2001-06, 2001-07, 2001-08, 2001-09, 2001-10, 2001-11, 2001-12, 2002-01...
- *rbihub* — sdmx-indices-of-reer-neer-monthly stale: last obs 2026-04-30 (173d) — mirror lag, patch the tail from another route
- *rbihub* — sdmx-forward-premia-inter-bank stale: last obs 2026-04-30 (173d) — mirror lag, patch the tail from another route
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
| `fx_AUD` | AUD per USD | 13959 | 1971-01-04 | 2026-09-11 |
| `fx_BRL` | BRL per USD | 7949 | 1995-01-02 | 2026-09-11 |
| `fx_CAD` | CAD per USD | 13972 | 1971-01-04 | 2026-09-11 |
| `fx_CHF` | CHF per USD | 13966 | 1971-01-04 | 2026-09-11 |
| `fx_CNY` | CNY per USD | 11406 | 1981-01-02 | 2026-09-11 |
| `fx_DKK` | DKK per USD | 13965 | 1971-01-04 | 2026-09-11 |
| `fx_EUR` | EUR per USD | 6945 | 1999-01-04 | 2026-09-11 |
| `fx_GBP` | GBP per USD | 13966 | 1971-01-04 | 2026-09-11 |
| `fx_HKD` | HKD per USD | 11466 | 1981-01-02 | 2026-09-11 |
| `fx_INR` | INR per USD | 13458 | 1973-01-02 | 2026-09-11 |
| `fx_JPY` | JPY per USD | 13960 | 1971-01-04 | 2026-09-11 |
| `fx_KRW` | KRW per USD | 11352 | 1981-04-13 | 2026-09-11 |
| `fx_MXN` | MXN per USD | 8234 | 1993-11-08 | 2026-09-11 |
| `fx_MYR` | MYR per USD | 13944 | 1971-01-04 | 2026-09-11 |
| `fx_NOK` | NOK per USD | 13965 | 1971-01-04 | 2026-09-11 |
| `fx_NZD` | NZD per USD | 13950 | 1971-01-04 | 2026-09-11 |
| `fx_SEK` | SEK per USD | 13965 | 1971-01-04 | 2026-09-11 |
| `fx_SGD` | SGD per USD | 11465 | 1981-01-02 | 2026-09-11 |
| `fx_THB` | THB per USD | 11385 | 1981-01-02 | 2026-09-11 |
| `fx_TWD` | TWD per USD | 10479 | 1983-10-03 | 2026-09-11 |
| `fx_ZAR` | ZAR per USD | 11709 | 1980-01-02 | 2026-09-11 |
| `brent_daily` | Brent crude, daily | 9087 | 1987-05-20 | 2026-09-15 |
| `wti_daily` | WTI crude, daily | 9502 | 1986-01-02 | 2026-09-15 |
| `vix_daily` | VIX close, daily | 9276 | 1990-01-02 | 2026-09-18 |
| `gold_monthly` | Gold USD/oz, monthly | 2324 | 1833-01 | 2026-08 |
| `us_cpi_monthly` | US CPI, monthly | 1362 | 1913-01-01 | 2026-07-01 |
| `us_10y_monthly` | US 10y yield, monthly | 880 | 1953-04-01 | 2026-07-01 |
