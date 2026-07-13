# Market Data Common Module — Implementation Plan

> **For agentic workers:** Execute inline in this session. Checkbox steps track progress.

**Goal:** Move shared market-data helpers out of `yfinance_client` into `common.py` so nothing imports shared symbols from `yfinance_client`.

**Architecture:** New `app/services/market_data/common.py` owns `MarketDataError`, `TICKER_INFO_KEYS`, clip/normalize/safe_float helpers, and `ohlcv_to_records`. Both clients import from `common` and thin-wrap `ohlcv_to_records`.

**Tech Stack:** Python, pandas, existing pytest suite.

---

### Task 1: Create `common.py`

- Create: `app/services/market_data/common.py`
- Move symbols from `yfinance_client.py` as specified in the design doc.

### Task 2: Update clients

- Modify: `yfinance_client.py`, `vnstock_client.py`
- Import shared symbols from `common`; remove duplicate definitions; wrap `ohlcv_to_records`.

### Task 3: Update consumers and tests

- Modify: `http_provider.py`, `backtest_service.py`, `api/routes/market.py`
- Modify: `tests/test_yfinance_client_tz.py`, `tests/test_market_ticker_search.py`

### Task 4: Verify

- Run relevant pytest modules
- Grep: no shared imports from `yfinance_client`
