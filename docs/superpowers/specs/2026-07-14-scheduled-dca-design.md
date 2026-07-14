# Scheduled DCA Strategy — Design

**Date:** 2026-07-14  
**Status:** Approved (verbal); awaiting spec review

## Problem

Simple Finance only offers Aggressive DCA (structural drawdown + SMA dip boost), with Standard DCA and lump-sum as baselines. Users cannot compare **when** cash is deployed (cadence / payday / skip) without changing dip logic.

## Goal

Add a second persisted strategy, `scheduled_dca`: fixed cash amounts on a configurable calendar schedule, **no dip boost**. Parallel module beside Aggressive DCA (Approach 1). Deliberate duplication of cash/shares accounting; cleanup later.

## Non-goals

- Dip overlay on Scheduled DCA
- Parameter optimization grid for schedule params
- Shared schedule/cash engine refactor (document only)
- DB schema / migration changes
- Multi-ticker portfolio strategies
- New dependencies

## Decision summary

| Choice | Decision |
|--------|----------|
| Strategy family | Same job as DCA: periodic cash-in on one ticker |
| Mechanism | Schedule variants (not formula sizing or new dip signals) |
| Shape | One strategy with cadence + day/weekday + optional skip |
| Dip | Schedule-only (contrast to Aggressive) |
| Implementation | Parallel module; note duplication for future cleanup |
| Persistence | Existing `strategy` string + `params` JSON; no migration |

## Injection rules

**Cash model**

- First row of the run: deploy `initial_cash` only (matches Aggressive: day-1 overwrites that day’s schedule amount; no double inject).
- Each later scheduled injection day: deploy `monthly_cash` (keep this API/field name for wire compatibility; UI label may say “period cash” / “weekly cash” by cadence).
- Buy at Open, apply `fee_rate`, same portfolio / return columns as Aggressive DCA.

**Schedule params**

| Param | Meaning | Default |
|-------|---------|---------|
| `cadence` | `weekly` \| `biweekly` \| `monthly` | `monthly` |
| `day_of_month` | 1–28; used when `cadence=monthly` | `1` |
| `weekday` | 0=Mon … 4=Fri; used when `cadence` is weekly or biweekly | `0` (Monday) |
| `skip_after_buy_n` | After a scheduled injection, skip the next N schedule hits (`0` = off) | `0` |

**Cadence semantics**

- **monthly:** target `day_of_month` each calendar month in range.
- **weekly:** each calendar week, target that `weekday`.
- **biweekly:** same weekday candidates as weekly, keep every other hit in chronological order (first eligible week in range fires, then skip one, etc.).

**Trading-day rule:** If the target calendar day is missing from the OHLCV index, use the **next** available trading day in range. If none remains before the next period’s target, skip that injection.

**Skip rule:** Applies only to scheduled injections (not day-1 `initial_cash`). After one fires, suppress the next `skip_after_buy_n` schedule hits.

## Architecture

### Backend

- New `run_scheduled_dca(...)` in `app/services/dca/scheduled.py` (Aggressive stays in `strategy.py`).
- Duplicate cash/shares accounting intentionally; mark with `ponytail:` naming the ceiling and upgrade path (shared schedule + cash applicator).
- `backtest_service` branches on request `strategy` (`aggressive_dca` default \| `scheduled_dca`):
  - Scheduled: no lookback/SMA optimize; run `run_scheduled_dca` → `run_standard_dca` + `run_benchmark` on that frame (cash-normalized baselines, same as today).
  - Persist `BacktestRun.strategy = "scheduled_dca"`; store schedule + cash + fee fields in `params`.
- Report: primary metrics/series key `scheduled_dca` plus `standard_dca` and `lump_sum`. Reuse plot/series builders with a small label/key parameter so the Aggressive path stays unchanged.
- API: `BacktestRequest` gains `strategy` and schedule fields. Validate ranges (`day_of_month` 1–28, etc.). Unused fields for a given cadence may be ignored; out-of-range values are rejected.

### Database

No migration. Existing columns:

- `strategy` → `"scheduled_dca"`
- `params` → cadence, day_of_month, weekday, skip_after_buy_n, initial_cash, monthly_cash, fee_rate

### Frontend

- Strategy selector on `BacktestForm`: Aggressive DCA vs Scheduled DCA.
- Aggressive: keep dip / optimize fields.
- Scheduled: show cadence, day_of_month or weekday (by cadence), skip_after_buy_n; hide dip / optimize.
- History and detail already expose `strategy`; ensure human-readable labels.

## Errors

- Empty OHLCV / empty after date filter → existing service errors.
- No injectable trading days in range → clear error: “No scheduled injection days in range.”
- Invalid numeric ranges on schedule params → API validation error.

## Comparison & metrics

- Baselines normalize to total cash deployed by the primary strategy (unchanged pattern).
- `dip_buys_triggered` remains `null` / unused for Scheduled.
- No new `scheduled_buys` metric in v1 (YAGNI); existing cash/return/Sharpe/CAGR/drawdown suffice.

## Testing

One small assert-based check (or tiny test file, no framework): synthetic OHLCV index + monthly `day_of_month=1` + `skip_after_buy_n=1` yields the expected injection mask (day-1 initial + every other monthly hit, with next-trading-day roll).

## Future cleanup (not in this change)

Extract:

1. Schedule-date / injection-mask generator
2. Shared “apply cash on mask → shares / portfolio / returns”

Both Aggressive and Scheduled call those helpers. Documented so implementers do not invent a premature abstraction in v1.

## Success criteria

- User can run and persist a `scheduled_dca` backtest with cadence / payday / skip params.
- Results appear in history filterable by strategy.
- Aggressive DCA behavior and API defaults remain unchanged when `strategy` is omitted or `aggressive_dca`.
- One runnable check covers injection-mask + skip + next-trading-day behavior.
