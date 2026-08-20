# Data manifest

Last run: **2026-08-20T12:44:14+00:00** · 124.2s · 0 errors, 9 warnings

| source | status | detail |
|---|---|---|
| `rbi_forward_book` | ok | n_months=92, parsed=92, last=2026-06, backfill_remaining=208, seconds=26.6 |
| `rbi_wss` | ok | n_weeks=120, last=2026-08-07, backfill_remaining=1269, seconds=18.0 |
| `rbihub` | ok | 4 series, seconds=1.6 |
| `nsdl_fpi` | ok | n=8, last=2026-08, backfill_remaining=19, seconds=29.9 |
| `india_misc` | ok | seconds=4.5 |
| `market` | ok | 27 series, seconds=43.5 |

## Warnings

- *market* — DGS10 (US 10y CMT, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- *market* — coverage gaps (8): DGS10, DGS2, DFII10, DFF, DTWEXBGS, BAMLEMCBPIOAS, TRESEGINM052N, RBINBIS — FRED-only series, no mirror exists; retried next run
- *rbihub* — sdmx-indices-of-reer-neer-monthly stale: last obs 2026-04-30 (141d) — mirror lag, patch the tail from another route
- *rbihub* — sdmx-forward-premia-inter-bank stale: last obs 2026-04-30 (141d) — mirror lag, patch the tail from another route
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
| `fx_AUD` | AUD per USD | 13940 | 1971-01-04 | 2026-08-14 |
| `fx_BRL` | BRL per USD | 7930 | 1995-01-02 | 2026-08-14 |
| `fx_CAD` | CAD per USD | 13953 | 1971-01-04 | 2026-08-14 |
| `fx_CHF` | CHF per USD | 13947 | 1971-01-04 | 2026-08-14 |
| `fx_CNY` | CNY per USD | 11387 | 1981-01-02 | 2026-08-14 |
| `fx_DKK` | DKK per USD | 13946 | 1971-01-04 | 2026-08-14 |
| `fx_EUR` | EUR per USD | 6926 | 1999-01-04 | 2026-08-14 |
| `fx_GBP` | GBP per USD | 13947 | 1971-01-04 | 2026-08-14 |
| `fx_HKD` | HKD per USD | 11447 | 1981-01-02 | 2026-08-14 |
| `fx_INR` | INR per USD | 13439 | 1973-01-02 | 2026-08-14 |
| `fx_JPY` | JPY per USD | 13941 | 1971-01-04 | 2026-08-14 |
| `fx_KRW` | KRW per USD | 11333 | 1981-04-13 | 2026-08-14 |
| `fx_MXN` | MXN per USD | 8215 | 1993-11-08 | 2026-08-14 |
| `fx_MYR` | MYR per USD | 13925 | 1971-01-04 | 2026-08-14 |
| `fx_NOK` | NOK per USD | 13946 | 1971-01-04 | 2026-08-14 |
| `fx_NZD` | NZD per USD | 13931 | 1971-01-04 | 2026-08-14 |
| `fx_SEK` | SEK per USD | 13946 | 1971-01-04 | 2026-08-14 |
| `fx_SGD` | SGD per USD | 11446 | 1981-01-02 | 2026-08-14 |
| `fx_THB` | THB per USD | 11366 | 1981-01-02 | 2026-08-14 |
| `fx_TWD` | TWD per USD | 10460 | 1983-10-03 | 2026-08-14 |
| `fx_ZAR` | ZAR per USD | 11690 | 1980-01-02 | 2026-08-14 |
| `brent_daily` | Brent crude, daily | 9958 | 1987-05-20 | 2026-08-18 |
| `wti_daily` | WTI crude, daily | 10226 | 1986-01-02 | 2026-08-18 |
| `vix_daily` | VIX close, daily | 9253 | 1990-01-02 | 2026-08-18 |
| `gold_monthly` | Gold USD/oz, monthly | 2323 | 1833-01 | 2026-07 |
| `us_cpi_monthly` | US CPI, monthly | 1361 | 1913-01-01 | 2026-06-01 |
| `us_10y_monthly` | US 10y yield, monthly | 879 | 1953-04-01 | 2026-06-01 |
