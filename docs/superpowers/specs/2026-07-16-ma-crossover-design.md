# MA Crossover Strategy — Design

**Date:** 2026-07-16  
**Status:** Approved

## Problem

Simple Finance backtests are DCA-only (`aggressive_dca`, `scheduled_dca`): cash injects and shares accumulate; there is no sell path. Users cannot compare a classic moving-average crossover (entry + exit) against buy-and-hold.

## Goal

Add a first buy/sell signal strategy, `ma_crossover`: long-only flip on fast/slow MA cross, lump-sum capital, next-open fills. Separate signal module and API beside DCA (Approach 2). Persist via existing `backtest_runs` with `strategy = "ma_crossover"`. Full-stack: engine, API, Nuxt form/charts/history.

## Non-goals

- Monthly / scheduled cash top-ups
- Short selling or partial position sizing
- Parameter optimization grid
- Generic signal-strategy framework / registry
- Refactoring DCA cash accounting into a shared engine
- DB schema / migration changes
- New dependencies

## Decision summary

| Choice | Decision |
|--------|----------|
| Position model | Long-only flip: 100% cash ↔ 100% invested |
| MA types | `sma` or `ema`, selectable in API/UI |
| Capital | Lump sum (`initial_cash`) only |
| Execution | Signal on day *t* close; fill at day *t+1* Open |
| Delivery | Full stack (backend + API + Nuxt) |
| Baselines | Buy & hold (`lump_sum`) + always cash (`idle_cash`) |
| Shape | Separate module + `POST /api/v1/backtest/ma-crossover` |
| Persistence | Existing `strategy` string + `params` JSON; no migration |
| Expansion path | Sized entries (B) or shorts (C) later reuse same fill loop |

## Trading rules

**Capital**

- Day 1 of the effective run: hold `initial_cash` in cash (no forced buy).
- No `monthly_cash` injections.

**Indicators**

| Param | Meaning | Default |
|-------|---------|---------|
| `ma_type` | `sma` \| `ema` | `sma` |
| `fast` | Fast MA period (bars) | `50` |
| `slow` | Slow MA period (bars) | `200` |

Validate `fast < slow` and both ≥ 1.

**Signal**

- Compute fast/slow MA on Close.
- **Golden cross:** previous bar had `fast ≤ slow`, current bar has `fast > slow`.
- **Death cross:** previous bar had `fast ≥ slow`, current bar has `fast < slow`.
- Crosses while already in the target state are ignored (no re-buy when long; no re-sell when flat).

**Execution**

- On golden cross at bar *t*: buy at bar *t+1* Open with all cash; shares = `cash * (1 - fee_rate) / Open`.
- On death cross at bar *t*: sell at bar *t+1* Open all shares; cash = `shares * Open * (1 - fee_rate)`.
- If the signal is on the last bar of the series, no fill (needs a next open).
- “Next open” means the next row in the OHLCV index (next trading day present), not calendar +1.

**Mark-to-market**

- Each bar: `Portfolio_Value = cash + shares * Close`.
- Strategy returns from portfolio value changes (no cash injection after start; `Total_Cash_Deployed` stays `initial_cash`).

## Architecture

```
POST /api/v1/backtest/ma-crossover
        │
        ▼
run_and_persist_ma_crossover()
        │
        ├── fetch_data()                 # existing
        ├── run_ma_crossover()           # NEW signals engine
        ├── lump_sum + idle_cash baselines
        ├── build report (reuse/adapt helpers)
        └── BacktestRun (strategy=ma_crossover)
```

### Backend

- New pure engine: `app/services/signals/ma_crossover.py` — no DB, no HTTP.
- New service entry: `run_and_persist_ma_crossover` in `backtest_service` (or thin sibling); do **not** overload `run_and_persist_dca_backtest` beyond a clear separate function.
- DCA modules (`app/services/dca/*`) stay unchanged for Aggressive/Scheduled paths.
- Report: primary key `ma_crossover`; baselines `lump_sum` and `idle_cash`. Adapt series/metrics builders so DCA paths keep `standard_dca` + `lump_sum` unchanged.
- Metrics: reuse return / CAGR / max DD / Sharpe. For this strategy only, add optional fields `buys_triggered` and `sells_triggered` (counts of executed fills). Leave `dip_buys_triggered` unused/`null`.

### API

- New schema `MaCrossoverRequest`: ticker, start_date, end_date, ma_type, fast, slow, initial_cash, fee_rate, visualization.
- `POST /api/v1/backtest/ma-crossover` → existing `BacktestReport` shape.
- Existing `GET /api/v1/backtest/runs` and `GET /runs/{id}` work via `strategy` string filter / stored row.

### Database

No migration.

- `strategy` → `"ma_crossover"`
- `params` → ma_type, fast, slow, initial_cash, fee_rate (and any effective dates already in result)

### Frontend

- Strategy selector adds “MA Crossover”.
- When selected: show `ma_type`, `fast`, `slow`, `initial_cash`, fee/dates/ticker; hide DCA-only fields (monthly cash, cadence, optimize, lookback, drawdown, SMA dip period).
- Store calls `POST /api/v1/backtest/ma-crossover` for this strategy; DCA strategies keep `/dca`.
- Charts / metrics / history: human-readable label and series keys for `ma_crossover`, `lump_sum`, `idle_cash`.

## Baselines

| Key | Behavior |
|-----|----------|
| `lump_sum` | Deploy `initial_cash` at first effective Open; hold shares to end (fee on buy). |
| `idle_cash` | Hold `initial_cash` as cash entire period; portfolio flat; returns ~0. |

Both share the MA strategy’s effective date index (after MA warm-up drop).

## Errors

- `end_date < start_date`, `fast >= slow`, invalid `ma_type` → **400**
- Empty OHLCV / provider failure → **400** via `BacktestServiceError`
- Too few bars after MA warm-up → **400** (“Test period too small after indicator warmup.”)
- Unexpected failure → **500**
- No crosses in range → success; stay in cash; still comparable to baselines

## Testing

One focused check (assert-based or small test file, no new framework):

- Synthetic Close series that produces one golden then one death cross.
- Assert buy fill at Open of the bar after the golden cross; sell fill at Open of the bar after the death cross.
- Assert end state is flat cash; fees reduce position as expected.

## Future expansion (not v1)

- Sized entries/exits: fraction of cash/shares per signal.
- Shorting: third position state.
- Additional signal strategies (RSI, MACD) as sibling modules under `app/services/signals/`.
- Optional MA overlay / trade markers on charts.
