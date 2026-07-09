# Simple Finance

FastAPI app for market data (yfinance wrapper) and Aggressive DCA backtesting with persisted results.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Run API

```bash
uvicorn app.main:app --reload
```

- Docs: http://127.0.0.1:8000/docs
- Health: `GET /health`

## Key endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/market/tickers/{ticker}` | Ticker info |
| GET | `/api/v1/market/tickers/{ticker}/ohlcv?start=&end=` | OHLCV bars |
| GET | `/api/v1/market/summary?symbols=` | Watchlist snapshot |
| POST | `/api/v1/backtest/dca` | Run + persist DCA backtest |
| GET | `/api/v1/backtest/runs?ticker=&strategy=` | List runs |
| GET | `/api/v1/backtest/runs/{id}` | Full stored report |

`visualization` on backtest: `series` (default), `images`, or `both`.

## Config

See `.env.example` for `DEFAULT_TICKER`, `DATABASE_URL`, market-data provider (`yfinance` / `http`), and watchlist symbols.

## CLI backtest (plots locally)

```bash
python dca_test.py
```

## Migrations

```bash
alembic upgrade head
```

On first API start, tables are also created via `init_db()` if missing.
