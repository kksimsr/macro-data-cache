# Data manifest

Last run: **2026-08-20T12:28:21+00:00** · 461.4s · 2 errors, 16 warnings

| source | status | detail |
|---|---|---|
| `fred` | **FAILED** | FetchError: FRED returned nothing at all. First error was: graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) |
| `rbi_forward_book` | ok | n_months=63, parsed=63, last=2026-06, backfill_remaining=237, seconds=28.1 |
| `rbi_wss` | ok | n_weeks=60, last=2026-08-07, backfill_remaining=1329, seconds=23.1 |
| `rbihub` | ok | 4 series, seconds=1.4 |
| `nsdl_fpi` | ok | n=8, last=2026-08, backfill_remaining=19, seconds=37.8 |
| `india_misc` | ok | seconds=6.7 |
| `market` | ok | 27 series, seconds=364.3 |

## Errors

- **rbi_forward_book** — 2023-12: net short -2,184 is a >75% collapse from 2023-11 (11,901) — suspect wrong cell
- **rbi_forward_book** — 2024-03: net short 541 is a >75% collapse from 2024-02 (-9,694) — suspect wrong cell

## Warnings

- *market* — DGS10 (US 10y CMT, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45)
- *market* — DGS2 (US 2y CMT, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45)
- *market* — DFII10 (US 10y TIPS real, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45)
- *market* — DFF (Fed funds effective, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45)
- *market* — DTWEXBGS (Broad USD index, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45)
- *market* — BAMLEMCBPIOAS (EM corporate OAS, daily) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45)
- *market* — TRESEGINM052N (India reserves excl gold, monthly (IMF IFS)) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45)
- *market* — RBINBIS (BIS real broad EER, India, monthly) unavailable from FRED: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45) | HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=45)
- *market* — coverage gaps (8): DGS10, DGS2, DFII10, DFF, DTWEXBGS, BAMLEMCBPIOAS, TRESEGINM052N, RBINBIS — FRED-only series, no mirror exists; retried next run
- *rbihub* — sdmx-indices-of-reer-neer-monthly stale: last obs 2026-04-30 (141d) — mirror lag, patch the tail from another route
- *rbihub* — sdmx-forward-premia-inter-bank stale: last obs 2026-04-30 (141d) — mirror lag, patch the tail from another route
- *nsdl_fpi* — 2021: postback failed after 3 tries (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2022: postback failed after 3 tries (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2023: postback failed after 3 tries (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2024: postback failed after 3 tries (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2025: postback failed after 3 tries (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))

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
