# Data manifest

Last run: **2026-11-08T09:21:40+00:00** · 102.1s · 0 errors, 13 warnings

| source | status | detail |
|---|---|---|
| `rbi_forward_book` | ok | n_months=166, parsed=162, last=2026-07, backfill_remaining=0, seconds=8.9 |
| `rbi_wss` | ok | n_weeks=891, last=2026-10-30, backfill_remaining=0, seconds=6.6 |
| `rbihub` | ok | 4 series, seconds=1.4 |
| `nsdl_fpi` | ok | n=10, last=2026-10, backfill_remaining=19, seconds=29.4 |
| `india_misc` | ok | seconds=8.6 |
| `market` | ok | 27 series, seconds=42.7 |
| `india_external` | ok | n=3, seconds=1.4 |
| `official_rates` | ok | n=3, seconds=3.1 |

## Warnings

- *india_misc* — very few strikes carry open interest — post-Apr-2024 liquidity is thin; treat IV-derived factors with suspicion
- *india_misc* — WPI 2022-23 base file not found for any recent month (site is known to be flaky — retry next run)
- *india_misc* — WPI 2011-12 base (needed for the pre-Apr-2023 splice) not found in the last 5 months — series may be discontinued
- *market* — vix_daily stale: last obs 2026-09-22 is 47d old (limit 10d)
- *market* — DGS10 (US 10y CMT, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- *market* — coverage gaps (8): DGS10, DGS2, DFII10, DFF, DTWEXBGS, BAMLEMCBPIOAS, TRESEGINM052N, RBINBIS — FRED-only series, no mirror exists; retried next run
- *rbi_forward_book* — 142 months given up on after 3 confirmed-absent probes: 2001-06, 2001-07, 2001-08, 2001-09, 2001-10, 2001-11, 2001-12, 2002-01...
- *rbihub* — sdmx-forward-premia-inter-bank stale: last obs 2026-06-30 (160d) — mirror lag, patch the tail from another route
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
| `fx_AUD` | AUD per USD | 13993 | 1971-01-04 | 2026-10-30 |
| `fx_BRL` | BRL per USD | 7983 | 1995-01-02 | 2026-10-30 |
| `fx_CAD` | CAD per USD | 14006 | 1971-01-04 | 2026-10-30 |
| `fx_CHF` | CHF per USD | 14000 | 1971-01-04 | 2026-10-30 |
| `fx_CNY` | CNY per USD | 11440 | 1981-01-02 | 2026-10-30 |
| `fx_DKK` | DKK per USD | 13999 | 1971-01-04 | 2026-10-30 |
| `fx_EUR` | EUR per USD | 6979 | 1999-01-04 | 2026-10-30 |
| `fx_GBP` | GBP per USD | 14000 | 1971-01-04 | 2026-10-30 |
| `fx_HKD` | HKD per USD | 11500 | 1981-01-02 | 2026-10-30 |
| `fx_INR` | INR per USD | 13492 | 1973-01-02 | 2026-10-30 |
| `fx_JPY` | JPY per USD | 13994 | 1971-01-04 | 2026-10-30 |
| `fx_KRW` | KRW per USD | 11386 | 1981-04-13 | 2026-10-30 |
| `fx_MXN` | MXN per USD | 8268 | 1993-11-08 | 2026-10-30 |
| `fx_MYR` | MYR per USD | 13978 | 1971-01-04 | 2026-10-30 |
| `fx_NOK` | NOK per USD | 13999 | 1971-01-04 | 2026-10-30 |
| `fx_NZD` | NZD per USD | 13984 | 1971-01-04 | 2026-10-30 |
| `fx_SEK` | SEK per USD | 13999 | 1971-01-04 | 2026-10-30 |
| `fx_SGD` | SGD per USD | 11499 | 1981-01-02 | 2026-10-30 |
| `fx_THB` | THB per USD | 11419 | 1981-01-02 | 2026-10-30 |
| `fx_TWD` | TWD per USD | 10513 | 1983-10-03 | 2026-10-30 |
| `fx_ZAR` | ZAR per USD | 11743 | 1980-01-02 | 2026-10-30 |
| `brent_daily` | Brent crude, daily | 9122 | 1987-05-20 | 2026-11-03 |
| `wti_daily` | WTI crude, daily | 9537 | 1986-01-02 | 2026-11-03 |
| `vix_daily` | VIX close, daily | 9278 | 1990-01-02 | 2026-09-22 |
| `gold_monthly` | Gold USD/oz, monthly | 2326 | 1833-01 | 2026-10 |
| `us_cpi_monthly` | US CPI, monthly | 1364 | 1913-01-01 | 2026-09-01 |
| `us_10y_monthly` | US 10y yield, monthly | 882 | 1953-04-01 | 2026-09-01 |
