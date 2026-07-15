# Scheduled DCA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second persisted backtest strategy, `scheduled_dca`, that deploys fixed cash on a configurable cadence/payday/skip schedule (no dip boost), parallel to Aggressive DCA.

**Architecture:** New `app/services/dca/scheduled.py` owns schedule mask + cash simulation (deliberate duplication; `ponytail:` note for later shared helper). `backtest_service` branches on `strategy`. Report/plot builders take a `primary_key` / `primary_label` so series/metrics keys are `scheduled_dca` or `aggressive_dca`. Frontend gains a strategy picker and schedule fields. No DB migration.

**Tech Stack:** Python, pandas, FastAPI/Pydantic, existing pytest, Nuxt 4 + Vuetify + ECharts.

## Global Constraints

- No dip overlay; no schedule-param optimize grid; no shared schedule engine refactor in this change
- No DB migration — use existing `strategy` string + `params` JSON
- Keep API field name `monthly_cash` (UI label may vary by cadence)
- Day-1 = `initial_cash` only (overwrite that day’s schedule amount; no double inject)
- Trading-day roll: missing target → next OHLCV day; else skip period
- Skip applies only to scheduled hits, not day-1 initial
- `weekday`: 0=Mon … 4=Fri; default 0
- `day_of_month`: 1–28; default 1
- `cadence`: `weekly` | `biweekly` | `monthly`; default `monthly`
- `skip_after_buy_n`: int ≥ 0; default 0
- Aggressive path defaults unchanged when `strategy` omitted or `aggressive_dca`
- One runnable check for injection mask + skip + next-trading-day
- Mark cash-accounting duplication with `ponytail:` ceiling + upgrade path

## File map

| File | Role |
|------|------|
| `app/services/dca/scheduled.py` | **Create** — schedule dates, injection mask, `run_scheduled_dca` |
| `tests/test_scheduled_dca.py` | **Create** — mask/skip/roll + empty-range errors |
| `app/services/dca/report.py` | Parameterize primary metrics/series key + label |
| `app/services/dca/plots.py` | Parameterize primary series label; empty dip scatter OK |
| `app/services/dca/__init__.py` | Export `run_scheduled_dca` |
| `app/api/schemas/backtest.py` | `strategy` + schedule fields + validation |
| `tests/test_backtest_request.py` | Schema validation cases |
| `app/services/backtest_service.py` | Branch on strategy; persist `scheduled_dca` |
| `app/api/routes/backtest.py` | Pass new request fields through |
| `frontend/app/types/api.ts` | Request + series key types |
| `frontend/app/stores/backtest.ts` | Default `strategy` + schedule fields |
| `frontend/app/components/backtest/BacktestForm.vue` | Strategy picker + conditional fields |
| `frontend/app/components/backtest/MetricsCards.vue` | Label for `scheduled_dca` |
| `frontend/app/components/charts/BacktestSeriesChart.vue` | Plot primary key dynamically |

---

### Task 1: Schedule engine + `run_scheduled_dca`

**Files:**
- Create: `app/services/dca/scheduled.py`
- Create: `tests/test_scheduled_dca.py`
- Modify: `app/services/dca/__init__.py`

**Interfaces:**
- Produces:
  - `build_injection_mask(index: pd.DatetimeIndex, *, cadence: str, day_of_month: int = 1, weekday: int = 0, skip_after_buy_n: int = 0) -> pd.Series[bool]` — True on scheduled injection days **after** day-1 (day-1 is handled in `run_scheduled_dca`, not by skip)
  - `run_scheduled_dca(df: pd.DataFrame, *, initial_cash: float = 10_000_000, monthly_cash: float = 1_000_000, fee_rate: float = 0.0015, cadence: str = "monthly", day_of_month: int = 1, weekday: int = 0, skip_after_buy_n: int = 0, annual_rf_rate: float = 0.05) -> tuple[pd.DataFrame, float]`
  - Returned frame columns (min): `Open`, `Close`, `Cash_Injected_Today`, `Shares_Bought`, `Total_Shares`, `Portfolio_Value`, `Total_Cash_Deployed`, `Strategy_Return`, `Execution_Signal` (always False — keeps report/plot dip path safe), `Is_Schedule_Day` (bool, scheduled hits that fired)
- Consumes: `calculate_sharpe` from `app.services.dca.metrics`

- [ ] **Step 1: Write the failing test**

Create `tests/test_scheduled_dca.py`:

```python
"""Scheduled DCA injection mask and cash simulation."""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.dca.scheduled import build_injection_mask, run_scheduled_dca


def _bday_ohlcv(start: str, periods: int) -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=periods)
    close = pd.Series(100.0, index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close},
        index=idx,
    )


def test_monthly_skip_and_next_trading_day_roll() -> None:
    # Jan 1 2021 is Friday New Year — not a business day; first bday is Jan 4.
    df = _bday_ohlcv("2021-01-04", periods=80)
    mask = build_injection_mask(
        df.index,
        cadence="monthly",
        day_of_month=1,
        skip_after_buy_n=1,
    )
    # Candidates after roll: ~Jan 4, Feb 1, Mar 1, Apr 1, ...
    # skip_after_buy_n=1 → keep Jan, skip Feb, keep Mar, skip Apr, ...
    fired = list(df.index[mask])
    assert fired[0] == pd.Timestamp("2021-01-04")
    assert pd.Timestamp("2021-02-01") not in fired
    assert fired[1] == pd.Timestamp("2021-03-01")


def test_run_scheduled_dca_day1_initial_only_no_double_inject() -> None:
    df = _bday_ohlcv("2021-01-04", periods=40)
    out, sharpe = run_scheduled_dca(
        df,
        initial_cash=10_000_000,
        monthly_cash=1_000_000,
        cadence="monthly",
        day_of_month=1,
        skip_after_buy_n=0,
    )
    assert out.iloc[0]["Cash_Injected_Today"] == 10_000_000
    # First schedule day coincides with day-1 → still initial only
    assert bool(out.iloc[0]["Is_Schedule_Day"]) is False or out.iloc[0]["Cash_Injected_Today"] == 10_000_000
    assert out["Execution_Signal"].sum() == 0
    assert out["Total_Cash_Deployed"].iloc[-1] > 10_000_000
    assert isinstance(sharpe, float)


def test_no_schedule_days_raises() -> None:
    df = _bday_ohlcv("2021-01-04", periods=2)
    with pytest.raises(ValueError, match="No scheduled injection"):
        run_scheduled_dca(df, cadence="monthly", day_of_month=1)
```

Note on day-1: implement so day-1 never sets `Is_Schedule_Day` True for cash purposes — schedule mask may mark that calendar slot, but `run_scheduled_dca` forces day-0 cash to `initial_cash` and does not add `monthly_cash`. Prefer clearing schedule flag on index position 0 when applying cash.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scheduled_dca.py -v`  
Expected: FAIL (import error / module missing)

- [ ] **Step 3: Implement `scheduled.py`**

Create `app/services/dca/scheduled.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.dca.metrics import calculate_sharpe

# ponytail: duplicates Aggressive cash/shares accounting and calendar injection.
# Ceiling: two strategies drift apart on fee/return formulas.
# Upgrade: extract schedule-mask generator + apply_cash_on_mask() shared by both.


def _next_trading_day(index: pd.DatetimeIndex, target: pd.Timestamp) -> pd.Timestamp | None:
    pos = index.searchsorted(target)
    if pos >= len(index):
        return None
    return index[pos]


def _monthly_targets(index: pd.DatetimeIndex, day_of_month: int) -> list[pd.Timestamp]:
    start = index[0].normalize()
    end = index[-1].normalize()
    targets: list[pd.Timestamp] = []
    cursor = pd.Timestamp(year=start.year, month=start.month, day=1)
    while cursor <= end:
        day = min(day_of_month, cursor.days_in_month)
        targets.append(pd.Timestamp(year=cursor.year, month=cursor.month, day=day))
        cursor = (cursor + pd.offsets.MonthBegin(1))
    return targets


def _weekly_targets(index: pd.DatetimeIndex, weekday: int) -> list[pd.Timestamp]:
    """One target per ISO week on the given weekday (0=Mon)."""
    start = index[0].normalize()
    end = index[-1].normalize()
    # Align to first date with that weekday on/after start's week Monday
    week_start = start - pd.Timedelta(days=start.weekday())
    targets: list[pd.Timestamp] = []
    cursor = week_start + pd.Timedelta(days=weekday)
    if cursor < start:
        cursor += pd.Timedelta(days=7)
    while cursor <= end + pd.Timedelta(days=7):
        targets.append(cursor)
        cursor += pd.Timedelta(days=7)
    return targets


def build_injection_mask(
    index: pd.DatetimeIndex,
    *,
    cadence: str,
    day_of_month: int = 1,
    weekday: int = 0,
    skip_after_buy_n: int = 0,
) -> pd.Series:
    if cadence == "monthly":
        raw = _monthly_targets(index, day_of_month)
    elif cadence in ("weekly", "biweekly"):
        raw = _weekly_targets(index, weekday)
    else:
        raise ValueError(f"Unsupported cadence: {cadence}")

    rolled: list[pd.Timestamp] = []
    for t in raw:
        hit = _next_trading_day(index, t)
        if hit is None:
            continue
        # Skip if rolled past next raw target's month/week boundary ambiguity:
        # accept hit if still before next target (when any)
        rolled.append(hit)

    # Dedupe while preserving order (roll collisions)
    seen: set[pd.Timestamp] = set()
    unique: list[pd.Timestamp] = []
    for h in rolled:
        if h not in seen:
            seen.add(h)
            unique.append(h)

    if cadence == "biweekly":
        unique = unique[::2]

    if skip_after_buy_n > 0:
        kept: list[pd.Timestamp] = []
        skip_left = 0
        for h in unique:
            if skip_left > 0:
                skip_left -= 1
                continue
            kept.append(h)
            skip_left = skip_after_buy_n
        unique = kept

    mask = pd.Series(False, index=index)
    for h in unique:
        mask.loc[h] = True
    return mask


def run_scheduled_dca(
    df: pd.DataFrame,
    *,
    initial_cash: float = 10_000_000,
    monthly_cash: float = 1_000_000,
    fee_rate: float = 0.0015,
    cadence: str = "monthly",
    day_of_month: int = 1,
    weekday: int = 0,
    skip_after_buy_n: int = 0,
    annual_rf_rate: float = 0.05,
) -> tuple[pd.DataFrame, float]:
    if df.empty:
        raise ValueError("No scheduled injection days in range.")

    data = df.copy()
    schedule = build_injection_mask(
        data.index,
        cadence=cadence,
        day_of_month=day_of_month,
        weekday=weekday,
        skip_after_buy_n=skip_after_buy_n,
    )
    # Day-1 initial overwrites schedule for position 0
    schedule.iloc[0] = False

    if not schedule.any() and len(data) < 2:
        # Still allow day-1-only if range is tiny but we require at least one
        # *scheduled* injection after day-1 per spec error message when none exist.
        raise ValueError("No scheduled injection days in range.")
    if not schedule.any():
        raise ValueError("No scheduled injection days in range.")

    data["Is_Schedule_Day"] = schedule
    data["Cash_Injected_Today"] = np.where(schedule, monthly_cash, 0.0)
    data.iloc[0, data.columns.get_loc("Cash_Injected_Today")] = initial_cash

    data["Shares_Bought"] = (data["Cash_Injected_Today"] * (1 - fee_rate)) / data["Open"]
    data["Total_Shares"] = data["Shares_Bought"].cumsum()
    data["Portfolio_Value"] = data["Total_Shares"] * data["Close"]
    data["Total_Cash_Deployed"] = data["Cash_Injected_Today"].cumsum()

    prev_value = data["Portfolio_Value"].shift(1)
    data["Strategy_Return"] = (
        data["Portfolio_Value"] - data["Cash_Injected_Today"] - prev_value
    ) / prev_value
    data["Strategy_Return"] = data["Strategy_Return"].fillna(0)
    data["Execution_Signal"] = False

    sharpe = calculate_sharpe(data["Strategy_Return"], annual_rf_rate=annual_rf_rate)
    return data, sharpe
```

Adjust the empty-range / no-schedule test if day-1-only runs are undesired — spec requires clear error when no scheduled injection days exist after applying rules.

Export from `app/services/dca/__init__.py`:

```python
from app.services.dca.scheduled import run_scheduled_dca
# add to __all__
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scheduled_dca.py -v`  
Expected: PASS (fix dates/assertions if calendar edge differs; keep semantics)

- [ ] **Step 5: Commit**

```bash
git add app/services/dca/scheduled.py app/services/dca/__init__.py tests/test_scheduled_dca.py
git commit -m "$(cat <<'EOF'
Add scheduled DCA strategy engine.

Implements cadence/payday/skip injection mask and cash simulation parallel to Aggressive DCA.
EOF
)"
```

---

### Task 2: Parameterize report + plots for primary strategy key

**Files:**
- Modify: `app/services/dca/report.py`
- Modify: `app/services/dca/plots.py`
- Modify: `tests/test_backtest_report.py`

**Interfaces:**
- Consumes: primary DataFrame from Task 1 or Aggressive (must include `Execution_Signal`)
- Produces:
  - `build_metrics(..., primary_key: str = "aggressive_dca", primary_label: str = "Aggressive DCA")`
  - `build_series(..., primary_key: str = "aggressive_dca")`
  - `build_backtest_report(..., primary_key: str = "aggressive_dca", primary_label: str = "Aggressive DCA")`
  - `build_performance_figure` / `render_performance_image` accept `primary_label: str = "Aggressive DCA (Drawdown Dips)"`

- [ ] **Step 1: Extend report test**

Add to `tests/test_backtest_report.py`:

```python
from app.services.dca.scheduled import run_scheduled_dca

def test_build_backtest_report_scheduled_primary_key() -> None:
    df = _sample_ohlcv(rows=80)
    primary, _ = run_scheduled_dca(df, cadence="monthly", day_of_month=1)
    std_df = run_standard_dca(primary)
    bench_df = run_benchmark(primary)
    report = build_backtest_report(
        primary,
        std_df,
        bench_df,
        params={"cadence": "monthly"},
        primary_key="scheduled_dca",
        primary_label="Scheduled DCA",
    )
    assert "scheduled_dca" in report["metrics"]
    assert "aggressive_dca" not in report["metrics"]
    assert "scheduled_dca" in report["series"]["portfolio_value"]
    assert report["metrics"]["scheduled_dca"]["dip_buys_triggered"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backtest_report.py::test_build_backtest_report_scheduled_primary_key -v`  
Expected: FAIL (unexpected kwargs / missing key)

- [ ] **Step 3: Update `report.py` and `plots.py`**

In `build_metrics`, use:

```python
frames = {
    primary_key: (primary_label, agg_dca_df),
    "standard_dca": ("Standard DCA", std_dca_df),
    "lump_sum": ("Lump Sum Benchmark", benchmark_df),
}
```

Keep dip count only when `name == "Aggressive DCA"`.

In `build_series`, replace hardcoded `"aggressive_dca"` keys with `primary_key`. Dip buys still read `Execution_Signal` (empty for scheduled).

Thread `primary_key` / `primary_label` through `build_backtest_report` → `build_metrics` / `build_series` / `render_performance_image`.

In `plots.py`, use `primary_label` for the primary line label; keep Standard / Lump Sum labels. Dip scatter stays; empty mask is fine.

- [ ] **Step 4: Run report tests**

Run: `pytest tests/test_backtest_report.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/dca/report.py app/services/dca/plots.py tests/test_backtest_report.py
git commit -m "$(cat <<'EOF'
Parameterize backtest report primary strategy key.

Lets Scheduled DCA reuse metrics/series/plots without hardcoding aggressive_dca.
EOF
)"
```

---

### Task 3: API schema, service branch, route wiring

**Files:**
- Modify: `app/api/schemas/backtest.py`
- Modify: `tests/test_backtest_request.py`
- Modify: `app/services/backtest_service.py`
- Modify: `app/api/routes/backtest.py`

**Interfaces:**
- Consumes: `run_scheduled_dca`, parameterized `build_backtest_report`
- Produces: `BacktestRequest.strategy: Literal["aggressive_dca", "scheduled_dca"] = "aggressive_dca"` plus schedule fields; `run_and_persist_dca_backtest(..., strategy=..., cadence=..., day_of_month=..., weekday=..., skip_after_buy_n=...)`

- [ ] **Step 1: Write schema tests**

Add to `tests/test_backtest_request.py`:

```python
def test_scheduled_strategy_defaults() -> None:
    body = BacktestRequest(
        start_date="2021-01-01",
        end_date="2022-01-01",
        strategy="scheduled_dca",
    )
    assert body.strategy == "scheduled_dca"
    assert body.cadence == "monthly"
    assert body.day_of_month == 1
    assert body.weekday == 0
    assert body.skip_after_buy_n == 0


def test_day_of_month_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        BacktestRequest(
            start_date="2021-01-01",
            end_date="2022-01-01",
            strategy="scheduled_dca",
            day_of_month=29,
        )


def test_default_strategy_remains_aggressive() -> None:
    body = BacktestRequest(start_date="2021-01-01", end_date="2022-01-01")
    assert body.strategy == "aggressive_dca"
```

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/test_backtest_request.py -v`  
Expected: FAIL on new fields

- [ ] **Step 3: Extend `BacktestRequest`**

```python
from typing import Literal

class BacktestRequest(BaseModel):
    # ...existing fields...
    strategy: Literal["aggressive_dca", "scheduled_dca"] = "aggressive_dca"
    cadence: Literal["weekly", "biweekly", "monthly"] = "monthly"
    day_of_month: int = Field(default=1, ge=1, le=28)
    weekday: int = Field(default=0, ge=0, le=4)
    skip_after_buy_n: int = Field(default=0, ge=0)
```

Unused schedule fields on Aggressive requests are ignored by the service (allowed).

- [ ] **Step 4: Branch `run_and_persist_dca_backtest`**

Signature additions:

```python
strategy: str = "aggressive_dca",
cadence: str = "monthly",
day_of_month: int = 1,
weekday: int = 0,
skip_after_buy_n: int = 0,
```

Logic sketch:

```python
if strategy == "scheduled_dca":
    params = {
        "cadence": cadence,
        "day_of_month": day_of_month,
        "weekday": weekday,
        "skip_after_buy_n": skip_after_buy_n,
        "initial_cash": cash0,
        "monthly_cash": cash_m,
        "fee_rate": fee,
        "optimized": False,
    }
    try:
        primary_df, _ = run_scheduled_dca(
            df,
            initial_cash=cash0,
            monthly_cash=cash_m,
            fee_rate=fee,
            cadence=cadence,
            day_of_month=day_of_month,
            weekday=weekday,
            skip_after_buy_n=skip_after_buy_n,
            annual_rf_rate=rf,
        )
    except ValueError as exc:
        raise BacktestServiceError(str(exc)) from exc
    primary_key = "scheduled_dca"
    primary_label = "Scheduled DCA"
else:
    # existing optimize / aggressive path unchanged
    primary_key = "aggressive_dca"
    primary_label = "Aggressive DCA"
    primary_df = agg_df  # from existing run_aggressive_dca

std_df = run_standard_dca(primary_df, fee_rate=fee)
bench_df = run_benchmark(primary_df, fee_rate=fee)
report = build_backtest_report(
    primary_df, std_df, bench_df,
    params=params,
    visualization=visualization,
    annual_rf_rate=rf,
    title_suffix=title_suffix,
    primary_key=primary_key,
    primary_label=primary_label,
)
metrics = report["metrics"][primary_key]
row = BacktestRun(strategy=primary_key, ..., sharpe=metrics["sharpe_ratio"], ...)
```

For scheduled: **do not** call `optimize_strategy` even if `optimize=True` (ignore optimize).

- [ ] **Step 5: Wire route**

In `create_dca_backtest`, pass `strategy=body.strategy`, `cadence=body.cadence`, `day_of_month=body.day_of_month`, `weekday=body.weekday`, `skip_after_buy_n=body.skip_after_buy_n`.

- [ ] **Step 6: Run schema + report tests**

Run: `pytest tests/test_backtest_request.py tests/test_backtest_report.py tests/test_scheduled_dca.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/api/schemas/backtest.py app/api/routes/backtest.py app/services/backtest_service.py tests/test_backtest_request.py
git commit -m "$(cat <<'EOF'
Wire scheduled_dca through API and backtest service.

Branches persistence and reports on strategy without a DB migration.
EOF
)"
```

---

### Task 4: Frontend strategy picker + schedule fields

**Files:**
- Modify: `frontend/app/types/api.ts`
- Modify: `frontend/app/stores/backtest.ts`
- Modify: `frontend/app/components/backtest/BacktestForm.vue`
- Modify: `frontend/app/components/backtest/MetricsCards.vue`
- Modify: `frontend/app/components/charts/BacktestSeriesChart.vue`

**Interfaces:**
- Consumes: API fields from Task 3
- Produces: form can POST `strategy: "scheduled_dca"` with schedule params; charts/metrics read primary key from series/metrics object

- [ ] **Step 1: Update types + store defaults**

`BacktestRequest`:

```typescript
strategy?: 'aggressive_dca' | 'scheduled_dca'
cadence?: 'weekly' | 'biweekly' | 'monthly'
day_of_month?: number | null
weekday?: number | null
skip_after_buy_n?: number | null
```

`BacktestSeries.portfolio_value` / `drawdown_pct`: allow index signature or optional `scheduled_dca`:

```typescript
portfolio_value: {
  aggressive_dca?: number[]
  scheduled_dca?: number[]
  standard_dca: number[]
  lump_sum: number[]
}
```

Store defaults: `strategy: 'aggressive_dca'`, `cadence: 'monthly'`, `day_of_month: 1`, `weekday: 0`, `skip_after_buy_n: 0`.

- [ ] **Step 2: Update `BacktestForm.vue`**

Add strategy select:

```vue
<v-select
  v-model="model.strategy"
  :items="[
    { title: 'Aggressive DCA', value: 'aggressive_dca' },
    { title: 'Scheduled DCA', value: 'scheduled_dca' },
  ]"
  label="Strategy"
  density="comfortable"
/>
```

Show optimize + lookback/drawdown/sma only when `model.strategy === 'aggressive_dca'`.

Show cadence / day_of_month / weekday / skip_after_buy_n when `scheduled_dca`.  
- `day_of_month` when cadence === `monthly`  
- `weekday` select (Mon–Fri → 0–4) when weekly/biweekly  
- Label for `monthly_cash`: “Monthly cash” vs “Period cash” by cadence

Submit button text: `Run backtest` (strategy-neutral).

- [ ] **Step 3: Metrics + chart labels**

`MetricsCards.vue`:

```typescript
scheduled_dca: 'Scheduled DCA',
```

`BacktestSeriesChart.vue`: derive primary series:

```typescript
const primaryKey = computed(() =>
  props.series.portfolio_value.scheduled_dca
    ? 'scheduled_dca'
    : 'aggressive_dca',
)
const primaryName = computed(() =>
  primaryKey.value === 'scheduled_dca' ? 'Scheduled DCA' : 'Aggressive DCA',
)
// use portfolio_value[primaryKey] for the first line
```

Dip scatter unchanged (empty for scheduled).

- [ ] **Step 4: Manual smoke (dev)**

With API running:

1. Aggressive DCA still runs with defaults  
2. Scheduled monthly day=1 skip=1 persists `strategy=scheduled_dca` and shows Scheduled metrics/chart  
3. History list shows strategy string

- [ ] **Step 5: Commit**

```bash
git add frontend/app/types/api.ts frontend/app/stores/backtest.ts \
  frontend/app/components/backtest/BacktestForm.vue \
  frontend/app/components/backtest/MetricsCards.vue \
  frontend/app/components/charts/BacktestSeriesChart.vue
git commit -m "$(cat <<'EOF'
Add Scheduled DCA strategy picker and schedule fields.

Frontend can run and display schedule-only backtests beside Aggressive DCA.
EOF
)"
```

---

### Task 5: Final verification

**Files:** none new

- [ ] **Step 1: Run full relevant pytest**

Run: `pytest tests/test_scheduled_dca.py tests/test_backtest_report.py tests/test_backtest_request.py -v`  
Expected: all PASS

- [ ] **Step 2: Spec checklist**

Confirm against `docs/superpowers/specs/2026-07-14-scheduled-dca-design.md`:

- [ ] `scheduled_dca` persists without migration  
- [ ] Schedule-only (no dip)  
- [ ] Cadence + day_of_month + weekday + skip  
- [ ] Day-1 initial only  
- [ ] Next-trading-day roll  
- [ ] Aggressive default unchanged  
- [ ] `ponytail:` note present  
- [ ] One runnable injection-mask check  

- [ ] **Step 3: Commit only if verification fixed stray files; otherwise done**

No empty commit.

---

## Spec coverage (self-review)

| Spec item | Task |
|-----------|------|
| `run_scheduled_dca` in `scheduled.py` | Task 1 |
| Cadence / payday / skip / roll / day-1 rules | Task 1 |
| Duplicate cash accounting + `ponytail:` | Task 1 |
| Report primary key `scheduled_dca` | Task 2 |
| Service branch, no optimize for scheduled | Task 3 |
| API fields + validation | Task 3 |
| Persist `strategy` + `params`, no migration | Task 3 |
| Frontend picker + conditional fields | Task 4 |
| Labels on metrics/history/chart | Task 4 |
| Runnable mask test | Task 1 |
| Error: no scheduled injection days | Task 1 + 3 |

## Out of scope (do not implement)

- Shared schedule/cash refactor  
- Dip overlay flag  
- Schedule parameter optimization  
- New `scheduled_buys` metric  
- DB migrations  
