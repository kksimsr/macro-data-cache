# Data manifest

Last run: **2026-10-19T08:02:06+00:00** · 100.7s · 0 errors, 13 warnings

| source | status | detail |
|---|---|---|
| `rbi_forward_book` | ok | n_months=166, parsed=162, last=2026-07, backfill_remaining=0, seconds=9.9 |
| `rbi_wss` | ok | n_weeks=888, last=2026-10-09, backfill_remaining=0, seconds=5.5 |
| `rbihub` | ok | 4 series, seconds=1.8 |
| `nsdl_fpi` | ok | n=9, last=2026-09, backfill_remaining=19, seconds=26.4 |
| `india_misc` | ok | seconds=8.4 |
| `market` | ok | 27 series, seconds=43.1 |
| `india_external` | ok | n=3, seconds=1.9 |
| `official_rates` | ok | n=3, seconds=3.8 |

## Warnings

- *india_misc* — very few strikes carry open interest — post-Apr-2024 liquidity is thin; treat IV-derived factors with suspicion
- *india_misc* — WPI 2022-23 base file not found for any recent month (site is known to be flaky — retry next run)
- *india_misc* — WPI 2011-12 base (needed for the pre-Apr-2023 splice) not found in the last 5 months — series may be discontinued
- *market* — vix_daily stale: last obs 2026-09-22 is 27d old (limit 10d)
- *market* — DGS10 (US 10y CMT, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- *market* — coverage gaps (8): DGS10, DGS2, DFII10, DFF, DTWEXBGS, BAMLEMCBPIOAS, TRESEGINM052N, RBINBIS — FRED-only series, no mirror exists; retried next run
- *rbi_forward_book* — 141 months given up on after 3 confirmed-absent probes: 2001-06, 2001-07, 2001-08, 2001-09, 2001-10, 2001-11, 2001-12, 2002-01...
- *rbihub* — sdmx-forward-premia-inter-bank stale: last obs 2026-06-30 (140d) — mirror lag, patch the tail from another route
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
| `fx_AUD` | AUD per USD | 13979 | 1971-01-04 | 2026-10-09 |
| `fx_BRL` | BRL per USD | 7969 | 1995-01-02 | 2026-10-09 |
| `fx_CAD` | CAD per USD | 13992 | 1971-01-04 | 2026-10-09 |
| `fx_CHF` | CHF per USD | 13986 | 1971-01-04 | 2026-10-09 |
| `fx_CNY` | CNY per USD | 11426 | 1981-01-02 | 2026-10-09 |
| `fx_DKK` | DKK per USD | 13985 | 1971-01-04 | 2026-10-09 |
| `fx_EUR` | EUR per USD | 6965 | 1999-01-04 | 2026-10-09 |
| `fx_GBP` | GBP per USD | 13986 | 1971-01-04 | 2026-10-09 |
| `fx_HKD` | HKD per USD | 11486 | 1981-01-02 | 2026-10-09 |
| `fx_INR` | INR per USD | 13478 | 1973-01-02 | 2026-10-09 |
| `fx_JPY` | JPY per USD | 13980 | 1971-01-04 | 2026-10-09 |
| `fx_KRW` | KRW per USD | 11372 | 1981-04-13 | 2026-10-09 |
| `fx_MXN` | MXN per USD | 8254 | 1993-11-08 | 2026-10-09 |
| `fx_MYR` | MYR per USD | 13964 | 1971-01-04 | 2026-10-09 |
| `fx_NOK` | NOK per USD | 13985 | 1971-01-04 | 2026-10-09 |
| `fx_NZD` | NZD per USD | 13970 | 1971-01-04 | 2026-10-09 |
| `fx_SEK` | SEK per USD | 13985 | 1971-01-04 | 2026-10-09 |
| `fx_SGD` | SGD per USD | 11485 | 1981-01-02 | 2026-10-09 |
| `fx_THB` | THB per USD | 11405 | 1981-01-02 | 2026-10-09 |
| `fx_TWD` | TWD per USD | 10499 | 1983-10-03 | 2026-10-09 |
| `fx_ZAR` | ZAR per USD | 11729 | 1980-01-02 | 2026-10-09 |
| `brent_daily` | Brent crude, daily | 9108 | 1987-05-20 | 2026-10-14 |
| `wti_daily` | WTI crude, daily | 9523 | 1986-01-02 | 2026-10-14 |
| `vix_daily` | VIX close, daily | 9278 | 1990-01-02 | 2026-09-22 |
| `gold_monthly` | Gold USD/oz, monthly | 2325 | 1833-01 | 2026-09 |
| `us_cpi_monthly` | US CPI, monthly | 1363 | 1913-01-01 | 2026-08-01 |
| `us_10y_monthly` | US 10y yield, monthly | 881 | 1953-04-01 | 2026-08-01 |
