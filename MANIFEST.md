# Data manifest

Last run: **2026-09-26T07:58:00+00:00** · 92.4s · 0 errors, 8 warnings

| source | status | detail |
|---|---|---|
| `rbi_forward_book` | ok | n_months=166, parsed=162, last=2026-07, backfill_remaining=0, seconds=4.3 |
| `rbi_wss` | ok | n_weeks=885, last=2026-09-18, backfill_remaining=0, seconds=6.1 |
| `rbihub` | ok | 4 series, seconds=1.2 |
| `nsdl_fpi` | ok | n=8, last=2026-08, backfill_remaining=19, seconds=25.6 |
| `india_misc` | ok | seconds=8.7 |
| `market` | ok | 27 series, seconds=42.6 |
| `india_external` | ok | n=3, seconds=1.3 |
| `official_rates` | ok | n=3, seconds=2.6 |

## Warnings

- *market* — DGS10 (US 10y CMT, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- *market* — coverage gaps (8): DGS10, DGS2, DFII10, DFF, DTWEXBGS, BAMLEMCBPIOAS, TRESEGINM052N, RBINBIS — FRED-only series, no mirror exists; retried next run
- *rbi_forward_book* — 141 months given up on after 3 confirmed-absent probes: 2001-06, 2001-07, 2001-08, 2001-09, 2001-10, 2001-11, 2001-12, 2002-01...
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
| `fx_AUD` | AUD per USD | 13964 | 1971-01-04 | 2026-09-18 |
| `fx_BRL` | BRL per USD | 7954 | 1995-01-02 | 2026-09-18 |
| `fx_CAD` | CAD per USD | 13977 | 1971-01-04 | 2026-09-18 |
| `fx_CHF` | CHF per USD | 13971 | 1971-01-04 | 2026-09-18 |
| `fx_CNY` | CNY per USD | 11411 | 1981-01-02 | 2026-09-18 |
| `fx_DKK` | DKK per USD | 13970 | 1971-01-04 | 2026-09-18 |
| `fx_EUR` | EUR per USD | 6950 | 1999-01-04 | 2026-09-18 |
| `fx_GBP` | GBP per USD | 13971 | 1971-01-04 | 2026-09-18 |
| `fx_HKD` | HKD per USD | 11471 | 1981-01-02 | 2026-09-18 |
| `fx_INR` | INR per USD | 13463 | 1973-01-02 | 2026-09-18 |
| `fx_JPY` | JPY per USD | 13965 | 1971-01-04 | 2026-09-18 |
| `fx_KRW` | KRW per USD | 11357 | 1981-04-13 | 2026-09-18 |
| `fx_MXN` | MXN per USD | 8239 | 1993-11-08 | 2026-09-18 |
| `fx_MYR` | MYR per USD | 13949 | 1971-01-04 | 2026-09-18 |
| `fx_NOK` | NOK per USD | 13970 | 1971-01-04 | 2026-09-18 |
| `fx_NZD` | NZD per USD | 13955 | 1971-01-04 | 2026-09-18 |
| `fx_SEK` | SEK per USD | 13970 | 1971-01-04 | 2026-09-18 |
| `fx_SGD` | SGD per USD | 11470 | 1981-01-02 | 2026-09-18 |
| `fx_THB` | THB per USD | 11390 | 1981-01-02 | 2026-09-18 |
| `fx_TWD` | TWD per USD | 10484 | 1983-10-03 | 2026-09-18 |
| `fx_ZAR` | ZAR per USD | 11714 | 1980-01-02 | 2026-09-18 |
| `brent_daily` | Brent crude, daily | 9092 | 1987-05-20 | 2026-09-22 |
| `wti_daily` | WTI crude, daily | 9507 | 1986-01-02 | 2026-09-22 |
| `vix_daily` | VIX close, daily | 9278 | 1990-01-02 | 2026-09-22 |
| `gold_monthly` | Gold USD/oz, monthly | 2324 | 1833-01 | 2026-08 |
| `us_cpi_monthly` | US CPI, monthly | 1362 | 1913-01-01 | 2026-07-01 |
| `us_10y_monthly` | US 10y yield, monthly | 880 | 1953-04-01 | 2026-07-01 |
