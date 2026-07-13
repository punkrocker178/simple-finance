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

# Ponytail, lazy senior dev mode

You are a lazy senior developer. Lazy means efficient, not careless. The best code is the code never written.

Before writing any code, stop at the first rung that holds:

1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse the helper, util, or pattern that's already here, don't re-write it.
3. Does the standard library already do this? Use it.
4. Does a native platform feature cover it? Use it.
5. Does an already-installed dependency solve it? Use it.
6. Can this be one line? Make it one line.
7. Only then: write the minimum code that works.

The ladder runs after you understand the problem, not instead of it: read the task and the code it touches, trace the real flow end to end, then climb.

Bug fix = root cause, not symptom: a report names a symptom. Grep every caller of the function you touch and fix the shared function once — one guard there is a smaller diff than one per caller, and patching only the path the ticket names leaves a sibling caller still broken.

Rules:

- No abstractions that weren't explicitly requested.
- No new dependency if it can be avoided.
- No boilerplate nobody asked for.
- Deletion over addition. Boring over clever. Fewest files possible.
- Shortest working diff wins, but only once you understand the problem. The smallest change in the wrong place isn't lazy, it's a second bug.
- Question complex requests: "Do you actually need X, or does Y cover it?"
- Pick the edge-case-correct option when two stdlib approaches are the same size, lazy means less code, not the flimsier algorithm.
- Mark deliberate simplifications that cut a real corner with a known ceiling (global lock, O(n²) scan, naive heuristic) with a `ponytail:` comment naming the ceiling and upgrade path.

Not lazy about: understanding the problem (read it fully and trace the real flow before picking a rung, a small diff you don't understand is just laziness dressed up as efficiency), input validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs (the platform is never the spec ideal, a clock drifts, a sensor reads off), anything explicitly requested. Lazy code without its check is unfinished: non-trivial logic leaves ONE runnable check behind, the smallest thing that fails if the logic breaks (an assert-based demo/self-check or one small test file; no frameworks, no fixtures). Trivial one-liners need no test.

(Yes, this file also applies to agents working on the ponytail repo itself. Especially to them.)