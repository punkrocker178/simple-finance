# Market Data Common Module — Design

**Date:** 2026-07-13  
**Status:** Approved (verbal); awaiting spec review

## Problem

`vnstock_client` imports shared helpers and types from `yfinance_client`, coupling a provider-agnostic facade to Yahoo Finance. Other modules (`http_provider`, `backtest_service`, `api/routes/market`) also import `MarketDataError` from `yfinance_client`. Nothing outside `yfinance_client` should depend on that module for shared code.

## Goal

Extract provider-neutral market-data utilities into `app/services/market_data/common.py`. Both clients and all other consumers import shared symbols from `common`. `yfinance_client` retains only Yahoo-specific logic.

## Non-goals

- Changing provider APIs or runtime behavior
- Renaming public client classes
- Splitting into multiple shared modules (`errors.py` / `utils.py`)

## Design

### New module: `app/services/market_data/common.py`

Owns:

| Symbol | Role |
|--------|------|
| `MarketDataError` | Shared exception for fetch/normalize failures |
| `TICKER_INFO_KEYS` | Canonical ticker-info field names |
| `clip_ohlcv_to_end_date` | Inclusive end-date clip for OHLCV frames |
| `normalize_vn_symbol` | Ensure `.VN` / `^` symbol form |
| `safe_float` | Coerce values to `float \| None` |
| `ohlcv_to_records` | DataFrame → list of date/OHLC dicts |

Private leading-underscore names (`_clip_ohlcv_to_end_date`, etc.) become public module functions without the underscore prefix once they live in `common` (they are shared API within the package). Call sites in both clients update accordingly.

`YFinanceClient.ohlcv_to_records` and `VnstockClient.ohlcv_to_records` become thin wrappers that call `common.ohlcv_to_records` (or staticmethods that delegate), preserving existing call sites that use `Client.ohlcv_to_records`.

Yahoo-only symbols stay in `yfinance_client`:

- `OHLCV_PERIOD_FALLBACKS`
- `OHLCV_FIVE_DAY_ONLY_TICKERS`
- `VN_EXCHANGES`
- `_is_vietnam_quote`

### Import rules

- Allowed from `yfinance_client`: `YFinanceClient` only (factory, providers, package `__init__`).
- `MarketDataError` and helpers: import from `common` everywhere else.
- `vnstock_client` must not import `yfinance_client`.

### Call sites to update

- `app/services/market_data/yfinance_client.py`
- `app/services/market_data/vnstock_client.py`
- `app/services/market_data/http_provider.py`
- `app/services/backtest_service.py`
- `app/api/routes/market.py`
- Tests that import helpers / `MarketDataError` from `yfinance_client` (`tests/test_yfinance_client_tz.py`, `tests/test_market_ticker_search.py`)

### Verification

- Existing unit tests for clip, symbol normalize, and clients still pass.
- Grep confirms no `from app.services.market_data.yfinance_client import` of shared symbols outside `YFinanceClient` itself / factory wiring.

## Alternatives considered

1. **`common.py` (chosen)** — single shared module; minimal churn.
2. **`errors.py` + `utils.py`** — clearer split; overkill for this surface.
3. **Extend `base.py`** — mixes Protocol with utilities.
