# Simple Finance

FastAPI app for market data (yfinance wrapper) and Aggressive DCA backtesting with persisted results. Nuxt 4 frontend under `frontend/`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
```

## Run API

```bash
uvicorn app.main:app --reload
```

- Docs: http://127.0.0.1:8000/docs
- Health: `GET /health`

## Run frontend

With the API on `:8000`:

```bash
cd frontend
npm run dev
```

- App: http://127.0.0.1:3000
- Browser calls go to `/api/backend/*` (Nitro proxy → FastAPI)
- SSR fetches use `NUXT_API_TARGET` (default `http://127.0.0.1:8000`)

## Key endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/market/tickers/search?q=&limit=` | Search Vietnamese tickers (yfinance) |
| GET | `/api/v1/market/tickers/{ticker}` | Ticker info |
| GET | `/api/v1/market/tickers/{ticker}/ohlcv?start=&end=` | OHLCV bars |
| GET | `/api/v1/market/summary?symbols=` | Watchlist snapshot |
| POST | `/api/v1/backtest/dca` | Run + persist DCA backtest |
| GET | `/api/v1/backtest/runs?ticker=&strategy=` | List runs |
| GET | `/api/v1/backtest/runs/{id}` | Full stored report |

`visualization` on backtest: `series` (default), `images`, or `both`.

## Config

See `.env.example` for `DEFAULT_TICKER`, `DATABASE_URL`, market-data provider (`yfinance` / `http`), and default `MARKET_SUMMARY_SYMBOLS` (used when `/summary` has no `symbols` param).

The homepage watchlist is stored in browser `localStorage` (`sf-watchlist`); add/remove tickers via the UI and pass the saved symbols to `/summary?symbols=`.

Frontend env: see [`frontend/.env.example`](frontend/.env.example).

## CLI backtest (plots locally)

```bash
python dca_test.py
```

## Migrations

```bash
alembic upgrade head
```

On first API start, tables are also created via `init_db()` if missing.
