# Simple Finance — Agent Instructions

FastAPI backend (`app/`) + Nuxt 4 frontend (`frontend/`). Market data via pluggable providers (`yfinance`, `vnstock`, `http`). DCA backtesting with persisted runs.

## Commands

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
alembic upgrade head

# Frontend
cd frontend && npm install && npm run dev
```

Config: `.env.example`. Market provider: `MARKET_DATA_PROVIDER` in `.env`.

## Code layout

| Path | Purpose |
|------|---------|
| `app/services/market_data/` | Provider clients (`vnstock_client.py`, `yfinance_client.py`) |
| `app/services/dca/` | Backtest strategy, metrics, plots |
| `app/api/routes/` | FastAPI endpoints |
| `frontend/` | Nuxt 4 UI |

Match existing patterns in neighboring files. Minimize scope; do not refactor unrelated code.

## Vnstock ecosystem

For **vnstock library** work (install, APIs, charts, news, pipeline), follow **[docs/AGENTS.md](docs/AGENTS.md)** and explore reference docs under `docs/`.

### Skills (auto-discovered)

Project skills live in `.cursor/skills/`. Read the matching `SKILL.md` when the task fits:

| Skill | When |
|-------|------|
| `vnstock-env-setup` | Install errors, environment setup, agent guide install |
| `vnstock-solution-architect` | App/script architecture, which library to use |
| `vnstock-migration-expert` | Free → sponsored tier migration |
| `vnstock-charting-expert` | Charts, plots, `vnstock_ezchart` |
| `vnstock-news-crawler` | News scraping |
| `vnstock-pipeline-cli` | Pipeline CLI tasks |
| `vnstock-pipeline-migration` | Pipeline v2.3+ upgrades |

Before writing `vnstock_data` code: check license tier (`~/.vnstock/auth_state.json`), use `show_api()` / `show_doc()`, and read the relevant file under `docs/`.

This app's vnstock integration is in `app/services/market_data/vnstock_client.py` — extend there rather than calling vnstock directly from routes.
