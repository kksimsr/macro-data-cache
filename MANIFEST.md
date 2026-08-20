# Data manifest

Last run: **2026-08-20T11:10:13+00:00** · 475.8s · 31 errors, 8 warnings

| source | status | detail |
|---|---|---|
| `fred` | **FAILED** | FetchError: FRED returned nothing at all. First error was: graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) |
| `rbi_forward_book` | ok | n_months=34, parsed=34, last=2026-06, backfill_remaining=267, seconds=8.4 |
| `rbi_wss` | ok | n_weeks=60, last=2026-08-14, backfill_remaining=1329, seconds=22.7 |
| `rbihub` | ok | 4 series, seconds=1.5 |
| `nsdl_fpi` | ok | n=8, last=2026-08, seconds=16.7 |
| `india_misc` | ok | seconds=4.3 |

## Errors

- **fred** — DEXINUS (USD/INR spot, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DTWEXBGS (Broad USD index, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DTWEXB (Broad USD index (legacy, ends 2019-12)) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DGS10 (US 10y CMT, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DFII10 (US 10y TIPS real, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DGS2 (US 2y CMT, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DFF (Fed funds effective, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — VIXCLS (VIX close, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — BAMLEMCBPIOAS (EM corporate OAS, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — CPIAUCSL (US CPI SA, monthly) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DCOILBRENTEU (Brent, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DCOILWTICO (WTI, daily) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — RBINBIS (BIS real broad EER India, monthly) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — TRESEGINM052N (India reserves excl gold, monthly) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — INDCPIALLMINMEI (India CPI (OECD) — STALE ~2025-03) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXCHUS (CNY/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXKOUS (KRW/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXTAUS (TWD/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXSIUS (SGD/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXTHUS (THB/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXMAUS (MYR/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXBZUS (BRL/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXMXUS (MXN/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXSFUS (ZAR/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXUSEU (USD/EUR) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXJPUS (JPY/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXUSUK (USD/GBP) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXCAUS (CAD/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXSDUS (SEK/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — DEXSZUS (CHF/USD) fetch failed -> graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)
- **fred** — source failed: FetchError: FRED returned nothing at all. First error was: graph: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20) | data: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=20)

## Warnings

- *rbihub* — sdmx-indices-of-reer-neer-monthly stale: last obs 2026-04-30 (141d) — mirror lag, patch the tail from another route
- *rbihub* — sdmx-forward-premia-inter-bank stale: last obs 2026-04-30 (141d) — mirror lag, patch the tail from another route
- *nsdl_fpi* — 2021: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2022: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2023: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2024: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2025: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — columns are positional (col1..colN) — map them once against the live header before use. Header seen:  | Monthly FPI Net Investments (Calendar Year - 2026) | Currency: INR USD | Calendar Year | INR Crores | Equity | Debt | Hybrid | Mutual Funds | Alternative Investment Funds(AIFs) | Total | Equity
