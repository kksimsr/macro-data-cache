# Data manifest

Last run: **2026-08-20T10:51:27+00:00** · 373.6s · 32 errors, 12 warnings

| source | status | detail |
|---|---|---|
| `fred` | **FAILED** | FetchError: FRED returned nothing at all — likely a network/egress problem |
| `rbi_forward_book` | ok | n_months=36, parsed=32, last=2026-08, backfill_remaining=267, seconds=12.9 |
| `rbi_wss` | **FAILED** | FetchError: WSS index parsed to zero dated links — layout changed |
| `rbihub` | ok | 4 series, seconds=1.7 |
| `nsdl_fpi` | ok | n=8, last=2026-08, seconds=12.7 |
| `india_misc` | ok | seconds=5.0 |

## Errors

- **fred** — DEXINUS (USD/INR spot, daily) fetch failed
- **fred** — DTWEXBGS (Broad USD index, daily) fetch failed
- **fred** — DTWEXB (Broad USD index (legacy, ends 2019-12)) fetch failed
- **fred** — DGS10 (US 10y CMT, daily) fetch failed
- **fred** — DFII10 (US 10y TIPS real, daily) fetch failed
- **fred** — DGS2 (US 2y CMT, daily) fetch failed
- **fred** — DFF (Fed funds effective, daily) fetch failed
- **fred** — VIXCLS (VIX close, daily) fetch failed
- **fred** — BAMLEMCBPIOAS (EM corporate OAS, daily) fetch failed
- **fred** — CPIAUCSL (US CPI SA, monthly) fetch failed
- **fred** — DCOILBRENTEU (Brent, daily) fetch failed
- **fred** — DCOILWTICO (WTI, daily) fetch failed
- **fred** — RBINBIS (BIS real broad EER India, monthly) fetch failed
- **fred** — TRESEGINM052N (India reserves excl gold, monthly) fetch failed
- **fred** — INDCPIALLMINMEI (India CPI (OECD) — STALE ~2025-03) fetch failed
- **fred** — DEXCHUS (CNY/USD) fetch failed
- **fred** — DEXKOUS (KRW/USD) fetch failed
- **fred** — DEXTAUS (TWD/USD) fetch failed
- **fred** — DEXSIUS (SGD/USD) fetch failed
- **fred** — DEXTHUS (THB/USD) fetch failed
- **fred** — DEXMAUS (MYR/USD) fetch failed
- **fred** — DEXBZUS (BRL/USD) fetch failed
- **fred** — DEXMXUS (MXN/USD) fetch failed
- **fred** — DEXSFUS (ZAR/USD) fetch failed
- **fred** — DEXUSEU (USD/EUR) fetch failed
- **fred** — DEXJPUS (JPY/USD) fetch failed
- **fred** — DEXUSUK (USD/GBP) fetch failed
- **fred** — DEXCAUS (CAD/USD) fetch failed
- **fred** — DEXSDUS (SEK/USD) fetch failed
- **fred** — DEXSZUS (CHF/USD) fetch failed
- **fred** — source failed: FetchError: FRED returned nothing at all — likely a network/egress problem
- **rbi_wss** — source failed: FetchError: WSS index parsed to zero dated links — layout changed

## Warnings

- *rbi_forward_book* — 2026-08: forward short position not parsed (raw archived)
- *rbi_forward_book* — 2026-07: forward short position not parsed (raw archived)
- *rbi_forward_book* — 2026-02: forward short position not parsed (raw archived)
- *rbi_forward_book* — 2025-02: forward short position not parsed (raw archived)
- *rbihub* — sdmx-indices-of-reer-neer-monthly stale: last obs 2026-04-30 (141d) — mirror lag, patch the tail from another route
- *rbihub* — sdmx-forward-premia-inter-bank stale: last obs 2026-04-30 (141d) — mirror lag, patch the tail from another route
- *nsdl_fpi* — 2021: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2022: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2023: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2024: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — 2025: postback failed (('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
- *nsdl_fpi* — columns are positional (col1..colN) — map them once against the live header before use. Header seen:  | Monthly FPI Net Investments (Calendar Year - 2026) | Currency: INR USD | Calendar Year | INR Crores | Equity | Debt | Hybrid | Mutual Funds | Alternative Investment Funds(AIFs) | Total | Equity
