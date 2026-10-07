# Data manifest

Last run: **2026-10-07T09:05:40+00:00** · 97.0s · 0 errors, 11 warnings

| source | status | detail |
|---|---|---|
| `rbi_forward_book` | ok | n_months=166, parsed=162, last=2026-07, backfill_remaining=0, seconds=8.2 |
| `rbi_wss` | ok | n_weeks=886, last=2026-09-25, backfill_remaining=0, seconds=5.7 |
| `rbihub` | ok | 4 series, seconds=0.6 |
| `nsdl_fpi` | ok | n=9, last=2026-09, backfill_remaining=19, seconds=23.3 |
| `india_misc` | ok | seconds=12.6 |
| `market` | ok | 27 series, seconds=42.8 |
| `india_external` | ok | n=3, seconds=0.6 |
| `official_rates` | ok | n=3, seconds=3.3 |

## Warnings

- *india_misc* — very few strikes carry open interest — post-Apr-2024 liquidity is thin; treat IV-derived factors with suspicion
- *market* — vix_daily stale: last obs 2026-09-22 is 15d old (limit 10d)
- *market* — DGS10 (US 10y CMT, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- *market* — coverage gaps (8): DGS10, DGS2, DFII10, DFF, DTWEXBGS, BAMLEMCBPIOAS, TRESEGINM052N, RBINBIS — FRED-only series, no mirror exists; retried next run
- *rbi_forward_book* — 141 months given up on after 3 confirmed-absent probes: 2001-06, 2001-07, 2001-08, 2001-09, 2001-10, 2001-11, 2001-12, 2002-01...
- *rbihub* — sdmx-forward-premia-inter-bank stale: last obs 2026-06-30 (128d) — mirror lag, patch the tail from another route
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
| `fx_AUD` | AUD per USD | 13974 | 1971-01-04 | 2026-10-02 |
| `fx_BRL` | BRL per USD | 7964 | 1995-01-02 | 2026-10-02 |
| `fx_CAD` | CAD per USD | 13987 | 1971-01-04 | 2026-10-02 |
| `fx_CHF` | CHF per USD | 13981 | 1971-01-04 | 2026-10-02 |
| `fx_CNY` | CNY per USD | 11421 | 1981-01-02 | 2026-10-02 |
| `fx_DKK` | DKK per USD | 13980 | 1971-01-04 | 2026-10-02 |
| `fx_EUR` | EUR per USD | 6960 | 1999-01-04 | 2026-10-02 |
| `fx_GBP` | GBP per USD | 13981 | 1971-01-04 | 2026-10-02 |
| `fx_HKD` | HKD per USD | 11481 | 1981-01-02 | 2026-10-02 |
| `fx_INR` | INR per USD | 13473 | 1973-01-02 | 2026-10-02 |
| `fx_JPY` | JPY per USD | 13975 | 1971-01-04 | 2026-10-02 |
| `fx_KRW` | KRW per USD | 11367 | 1981-04-13 | 2026-10-02 |
| `fx_MXN` | MXN per USD | 8249 | 1993-11-08 | 2026-10-02 |
| `fx_MYR` | MYR per USD | 13959 | 1971-01-04 | 2026-10-02 |
| `fx_NOK` | NOK per USD | 13980 | 1971-01-04 | 2026-10-02 |
| `fx_NZD` | NZD per USD | 13965 | 1971-01-04 | 2026-10-02 |
| `fx_SEK` | SEK per USD | 13980 | 1971-01-04 | 2026-10-02 |
| `fx_SGD` | SGD per USD | 11480 | 1981-01-02 | 2026-10-02 |
| `fx_THB` | THB per USD | 11400 | 1981-01-02 | 2026-10-02 |
| `fx_TWD` | TWD per USD | 10494 | 1983-10-03 | 2026-10-02 |
| `fx_ZAR` | ZAR per USD | 11724 | 1980-01-02 | 2026-10-02 |
| `brent_daily` | Brent crude, daily | 9097 | 1987-05-20 | 2026-09-29 |
| `wti_daily` | WTI crude, daily | 9512 | 1986-01-02 | 2026-09-29 |
| `vix_daily` | VIX close, daily | 9278 | 1990-01-02 | 2026-09-22 |
| `gold_monthly` | Gold USD/oz, monthly | 2325 | 1833-01 | 2026-09 |
| `us_cpi_monthly` | US CPI, monthly | 1363 | 1913-01-01 | 2026-08-01 |
| `us_10y_monthly` | US 10y yield, monthly | 881 | 1953-04-01 | 2026-08-01 |
