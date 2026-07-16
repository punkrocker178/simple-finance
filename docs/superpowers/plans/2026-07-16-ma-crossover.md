# MA Crossover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a long-only MA crossover backtest (`ma_crossover`) with SMA/EMA, next-open fills, lump-sum capital, buy&hold + idle-cash baselines, persisted runs, and Nuxt UI.

**Architecture:** New pure engine under `app/services/signals/` plus `POST /api/v1/backtest/ma-crossover`. DCA path stays untouched. Reuse `BacktestRun` persistence and adapt report helpers for signal baselines. Frontend branches endpoint/form fields by strategy.

**Tech Stack:** Python, pandas, FastAPI/Pydantic, existing pytest, Nuxt 4 + Vuetify + ECharts.

## Global Constraints

- Long-only flip only (all cash ↔ all shares); no shorts, no partial sizing
- Lump sum only — no monthly cash injections
- `ma_type`: `sma` | `ema`; defaults SMA 50/200; require `fast < slow`
- Signal on day *t* Close MAs; fill at next trading row’s Open
- Cross = relative position flip vs prior bar; ignore cross when already in target state
- Last-bar signal has no fill
- Baselines: `lump_sum` (buy day-1 open) + `idle_cash` (flat cash)
- Separate route/service from DCA; no DB migration; no new deps; no optimize grid
- One runnable check for cross → next-open buy/sell + fees
- Metrics: add `buys_triggered` / `sells_triggered`; leave `dip_buys_triggered` null

## File map

| File | Role |
|------|------|
| `app/services/signals/__init__.py` | **Create** — export `run_ma_crossover` |
| `app/services/signals/ma_crossover.py` | **Create** — MA engine + baselines |
| `tests/test_ma_crossover.py` | **Create** — synthetic cross/fill/fee tests |
| `app/services/signals/report.py` | **Create** — signal report builder (metrics/series) |
| `tests/test_signal_report.py` | **Create** — report keys for MA path |
| `app/api/schemas/backtest.py` | Add `MaCrossoverRequest` + metric optional fields |
| `tests/test_backtest_request.py` | Schema validation for MA request |
| `app/services/backtest_service.py` | Add `run_and_persist_ma_crossover` |
| `app/api/routes/backtest.py` | Add `POST /ma-crossover` |
| `frontend/app/types/api.ts` | MA request + series/metric types |
| `frontend/app/stores/backtest.ts` | Branch endpoint; MA form fields |
| `frontend/app/components/backtest/BacktestForm.vue` | Strategy + MA fields |
| `frontend/app/components/backtest/MetricsCards.vue` | Labels + buy/sell counts |
| `frontend/app/components/charts/BacktestSeriesChart.vue` | MA series keys |
| `frontend/app/pages/backtest/index.vue` | Copy/title for signal strategies |

---

### Task 1: MA crossover engine + baselines

**Files:**
- Create: `app/services/signals/__init__.py`
- Create: `app/services/signals/ma_crossover.py`
- Create: `tests/test_ma_crossover.py`

**Interfaces:**
- Produces:
  - `run_ma_crossover(df: pd.DataFrame, *, ma_type: str = "sma", fast: int = 50, slow: int = 200, initial_cash: float = 10_000_000, fee_rate: float = 0.0015, annual_rf_rate: float = 0.05) -> tuple[pd.DataFrame, float]`
  - Returned frame columns (min): `Open`, `Close`, `Fast_MA`, `Slow_MA`, `Buy_Fill`, `Sell_Fill`, `Cash`, `Shares`, `Portfolio_Value`, `Total_Cash_Deployed`, `Strategy_Return`, `Execution_Signal` (True on buy fills only — keeps optional scatter reuse safe)
  - `run_lump_sum_baseline(index_df: pd.DataFrame, *, initial_cash: float, fee_rate: float) -> pd.DataFrame` — buy all on first Open; columns: `Close`, `Portfolio_Value`, `Strategy_Return`, `Total_Cash_Deployed`
  - `run_idle_cash_baseline(index_df: pd.DataFrame, *, initial_cash: float) -> pd.DataFrame` — flat cash; same column set
- Consumes: `calculate_sharpe` from `app.services.dca.metrics`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ma_crossover.py`:

```python
"""MA crossover signals and next-open fills."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.signals.ma_crossover import (
    run_idle_cash_baseline,
    run_lump_sum_baseline,
    run_ma_crossover,
)


def _ohlcv_from_close(close: list[float], start: str = "2021-01-04") -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=len(close))
    c = pd.Series(close, index=idx, dtype=float)
    # Open = prior close (first open = first close) so fills are predictable
    o = c.shift(1).fillna(c.iloc[0])
    return pd.DataFrame({"Open": o, "High": c + 1, "Low": c - 1, "Close": c}, index=idx)


def test_golden_then_death_fills_next_open() -> None:
    # Craft closes so SMA(3) crosses SMA(5) up then down.
    # Long stretch low, jump high, then drop low again.
    close = [10.0] * 8 + [20.0] * 8 + [5.0] * 8
    df = _ohlcv_from_close(close)
    out, sharpe = run_ma_crossover(
        df,
        ma_type="sma",
        fast=3,
        slow=5,
        initial_cash=10_000.0,
        fee_rate=0.0,
    )
    assert not out.empty
    buys = out.index[out["Buy_Fill"]]
    sells = out.index[out["Sell_Fill"]]
    assert len(buys) >= 1
    assert len(sells) >= 1
    # First buy must be strictly after the first golden-signal bar (next open).
    fast = out["Fast_MA"]
    slow = out["Slow_MA"]
    golden = (fast.shift(1) <= slow.shift(1)) & (fast > slow)
    first_golden = out.index[golden][0]
    assert buys[0] > first_golden
    # End flat in cash after death cross fill
    assert out["Shares"].iloc[-1] == 0.0
    assert out["Cash"].iloc[-1] > 0.0
    assert out["Total_Cash_Deployed"].iloc[-1] == 10_000.0
    assert isinstance(sharpe, float)


def test_fee_applied_on_buy_and_sell() -> None:
    close = [10.0] * 8 + [20.0] * 8 + [5.0] * 8
    df = _ohlcv_from_close(close)
    out, _ = run_ma_crossover(
        df, ma_type="sma", fast=3, slow=5, initial_cash=10_000.0, fee_rate=0.01
    )
    buy_row = out.loc[out["Buy_Fill"]].iloc[0]
    # With 1% fee, shares < cash/open
    assert buy_row["Shares"] == pytest.approx(
        (10_000.0 * 0.99) / buy_row["Open"], rel=1e-9
    )
    sell_rows = out.loc[out["Sell_Fill"]]
    assert len(sell_rows) >= 1
    # After sell, cash < shares_before * open (fee)
    assert out["Cash"].iloc[-1] < 10_000.0


def test_fast_ge_slow_raises() -> None:
    df = _ohlcv_from_close([100.0] * 30)
    with pytest.raises(ValueError, match="fast"):
        run_ma_crossover(df, fast=50, slow=50)


def test_ema_runs() -> None:
    df = _ohlcv_from_close([10.0] * 8 + [20.0] * 8 + [5.0] * 8)
    out, _ = run_ma_crossover(df, ma_type="ema", fast=3, slow=5, initial_cash=1_000.0)
    assert "Fast_MA" in out.columns
    assert not out.empty


def test_baselines() -> None:
    df = _ohlcv_from_close([100.0, 110.0, 90.0, 95.0])
    primary, _ = run_ma_crossover(df, fast=2, slow=3, initial_cash=1_000.0, fee_rate=0.0)
    lump = run_lump_sum_baseline(primary, initial_cash=1_000.0, fee_rate=0.0)
    idle = run_idle_cash_baseline(primary, initial_cash=1_000.0)
    assert lump["Portfolio_Value"].iloc[0] == pytest.approx(1_000.0)
    assert idle["Portfolio_Value"].iloc[-1] == pytest.approx(1_000.0)
    assert (idle["Strategy_Return"] == 0).all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ma_crossover.py -v`  
Expected: FAIL (import error / module missing)

- [ ] **Step 3: Implement engine**

Create `app/services/signals/ma_crossover.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.dca.metrics import calculate_sharpe


def run_ma_crossover(
    df: pd.DataFrame,
    *,
    ma_type: str = "sma",
    fast: int = 50,
    slow: int = 200,
    initial_cash: float = 10_000_000,
    fee_rate: float = 0.0015,
    annual_rf_rate: float = 0.05,
) -> tuple[pd.DataFrame, float]:
    if fast < 1 or slow < 1:
        raise ValueError("fast and slow must be >= 1")
    if fast >= slow:
        raise ValueError("fast must be less than slow")

    data = df.copy()
    if ma_type == "sma":
        data["Fast_MA"] = data["Close"].rolling(window=fast).mean()
        data["Slow_MA"] = data["Close"].rolling(window=slow).mean()
    elif ma_type == "ema":
        data["Fast_MA"] = data["Close"].ewm(span=fast, adjust=False).mean()
        data["Slow_MA"] = data["Close"].ewm(span=slow, adjust=False).mean()
    else:
        raise ValueError(f"Unsupported ma_type: {ma_type}")

    test = data.dropna(subset=["Fast_MA", "Slow_MA"]).copy()
    if test.empty:
        return test, 0.0

    fast_s = test["Fast_MA"]
    slow_s = test["Slow_MA"]
    golden = (fast_s.shift(1) <= slow_s.shift(1)) & (fast_s > slow_s)
    death = (fast_s.shift(1) >= slow_s.shift(1)) & (fast_s < slow_s)
    # Execute next bar
    buy_pending = golden.shift(1).fillna(False).astype(bool)
    sell_pending = death.shift(1).fillna(False).astype(bool)

    cash = float(initial_cash)
    shares = 0.0
    cash_col: list[float] = []
    shares_col: list[float] = []
    buy_fill: list[bool] = []
    sell_fill: list[bool] = []
    pv_col: list[float] = []

    for ts, row in test.iterrows():
        bought = False
        sold = False
        if bool(buy_pending.loc[ts]) and shares == 0.0 and cash > 0.0:
            shares = (cash * (1.0 - fee_rate)) / float(row["Open"])
            cash = 0.0
            bought = True
        if bool(sell_pending.loc[ts]) and shares > 0.0:
            cash = shares * float(row["Open"]) * (1.0 - fee_rate)
            shares = 0.0
            sold = True
        pv = cash + shares * float(row["Close"])
        cash_col.append(cash)
        shares_col.append(shares)
        buy_fill.append(bought)
        sell_fill.append(sold)
        pv_col.append(pv)

    test["Cash"] = cash_col
    test["Shares"] = shares_col
    test["Buy_Fill"] = buy_fill
    test["Sell_Fill"] = sell_fill
    test["Portfolio_Value"] = pv_col
    test["Total_Cash_Deployed"] = float(initial_cash)
    test["Execution_Signal"] = test["Buy_Fill"]
    prev = test["Portfolio_Value"].shift(1)
    test["Strategy_Return"] = (test["Portfolio_Value"] - prev) / prev
    test["Strategy_Return"] = test["Strategy_Return"].fillna(0.0)

    sharpe = calculate_sharpe(test["Strategy_Return"], annual_rf_rate=annual_rf_rate)
    return test, sharpe


def run_lump_sum_baseline(
    index_df: pd.DataFrame,
    *,
    initial_cash: float,
    fee_rate: float,
) -> pd.DataFrame:
    out = pd.DataFrame(index=index_df.index)
    out["Close"] = index_df["Close"]
    open0 = float(index_df["Open"].iloc[0])
    shares = (initial_cash * (1.0 - fee_rate)) / open0
    out["Portfolio_Value"] = shares * out["Close"]
    out["Strategy_Return"] = out["Portfolio_Value"].pct_change().fillna(0.0)
    out["Total_Cash_Deployed"] = float(initial_cash)
    return out


def run_idle_cash_baseline(
    index_df: pd.DataFrame,
    *,
    initial_cash: float,
) -> pd.DataFrame:
    out = pd.DataFrame(index=index_df.index)
    out["Close"] = index_df["Close"]
    out["Portfolio_Value"] = float(initial_cash)
    out["Strategy_Return"] = 0.0
    out["Total_Cash_Deployed"] = float(initial_cash)
    return out
```

Create `app/services/signals/__init__.py`:

```python
from app.services.signals.ma_crossover import (
    run_idle_cash_baseline,
    run_lump_sum_baseline,
    run_ma_crossover,
)

__all__ = [
    "run_ma_crossover",
    "run_lump_sum_baseline",
    "run_idle_cash_baseline",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ma_crossover.py -v`  
Expected: PASS (if synthetic crosses are weak, lengthen high/low plateaus until asserts hold; keep next-open semantics)

- [ ] **Step 5: Commit**

```bash
git add app/services/signals/ tests/test_ma_crossover.py
git commit -m "$(cat <<'EOF'
Add MA crossover signal engine.

Long-only flip on SMA/EMA cross with next-open fills and cash/lump-sum baselines.
EOF
)"
```

---

### Task 2: Signal report builder

**Files:**
- Create: `app/services/signals/report.py`
- Create: `tests/test_signal_report.py`

**Interfaces:**
- Produces:
  - `build_signal_backtest_report(primary_df, lump_sum_df, idle_cash_df, *, params, visualization="series", annual_rf_rate=0.05, primary_key="ma_crossover", primary_label="MA Crossover") -> dict`
  - Report shape matches DCA report: `params`, `metrics`, `effective_start_date`, `effective_end_date`, `series`, `images`
  - `metrics[primary_key]` includes `buys_triggered`, `sells_triggered`; `dip_buys_triggered` is `None`
  - `series.portfolio_value` keys: `primary_key`, `lump_sum`, `idle_cash` (no `standard_dca`)
- Consumes: `calculate_cagr`, `calculate_sharpe` from `app.services.dca.metrics`; optionally `render_performance_image` only if easy — otherwise `images=None` for signal path when visualization is images (prefer implementing a thin plot reuse or skip images for v1 and map `images`/`both` → series-only with note). **v1 decision:** support `series` fully; for `images`/`both`, set `images` to `None` and still return series when `both` (ponytail: plot reuse later).

- [ ] **Step 1: Write the failing test**

Create `tests/test_signal_report.py`:

```python
"""Signal strategy backtest report shape."""

from __future__ import annotations

import pandas as pd

from app.services.signals.ma_crossover import (
    run_idle_cash_baseline,
    run_lump_sum_baseline,
    run_ma_crossover,
)
from app.services.signals.report import build_signal_backtest_report


def _ohlcv(rows: int = 40) -> pd.DataFrame:
    idx = pd.bdate_range("2021-01-04", periods=rows)
    close = pd.Series([10.0] * 15 + [20.0] * 15 + [5.0] * (rows - 30), index=idx)
    open_ = close.shift(1).fillna(close.iloc[0])
    return pd.DataFrame(
        {"Open": open_, "High": close + 1, "Low": close - 1, "Close": close},
        index=idx,
    )


def test_signal_report_keys_and_trade_counts() -> None:
    df = _ohlcv()
    primary, _ = run_ma_crossover(df, fast=3, slow=5, initial_cash=10_000.0, fee_rate=0.0)
    lump = run_lump_sum_baseline(primary, initial_cash=10_000.0, fee_rate=0.0)
    idle = run_idle_cash_baseline(primary, initial_cash=10_000.0)
    report = build_signal_backtest_report(
        primary,
        lump,
        idle,
        params={"ma_type": "sma", "fast": 3, "slow": 5},
        visualization="series",
    )
    assert "ma_crossover" in report["metrics"]
    assert "lump_sum" in report["metrics"]
    assert "idle_cash" in report["metrics"]
    assert "standard_dca" not in report["metrics"]
    m = report["metrics"]["ma_crossover"]
    assert m["dip_buys_triggered"] is None
    assert m["buys_triggered"] == int(primary["Buy_Fill"].sum())
    assert m["sells_triggered"] == int(primary["Sell_Fill"].sum())
    assert "ma_crossover" in report["series"]["portfolio_value"]
    assert "idle_cash" in report["series"]["portfolio_value"]
    assert report["effective_start_date"] == primary.index[0].strftime("%Y-%m-%d")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_signal_report.py -v`  
Expected: FAIL (module missing)

- [ ] **Step 3: Implement `app/services/signals/report.py`**

```python
from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from app.services.dca.metrics import calculate_cagr, calculate_sharpe

VisualizationMode = Literal["series", "images", "both"]


def _metrics(
    name: str,
    df: pd.DataFrame,
    *,
    annual_rf_rate: float,
    buys: int | None = None,
    sells: int | None = None,
) -> dict[str, Any]:
    total_cash_in = float(df["Total_Cash_Deployed"].iloc[-1])
    final_val = float(df["Portfolio_Value"].iloc[-1])
    ret = ((final_val / total_cash_in) - 1) * 100 if total_cash_in else 0.0
    days = (df.index[-1] - df.index[0]).days
    cagr = calculate_cagr(ret, days)
    peak = df["Portfolio_Value"].cummax()
    dd = float(((df["Portfolio_Value"] - peak) / peak).min() * 100) if len(df) else 0.0
    sharpe = calculate_sharpe(df["Strategy_Return"], annual_rf_rate=annual_rf_rate)
    return {
        "total_cash_injected": total_cash_in,
        "final_portfolio_value": final_val,
        "total_return_pct": float(ret),
        "cagr_pct": float(cagr),
        "max_drawdown_pct": dd,
        "sharpe_ratio": float(sharpe),
        "dip_buys_triggered": None,
        "buys_triggered": buys,
        "sells_triggered": sells,
    }


def _drawdown_series(values: pd.Series) -> list[float]:
    peak = values.cummax()
    dd = (values - peak) / peak * 100
    return [float(x) for x in dd.tolist()]


def _monthly_growth(values: pd.Series) -> dict[str, list]:
    monthly = values.resample("ME").last().pct_change().fillna(0) * 100
    return {
        "dates": [d.strftime("%Y-%m") for d in monthly.index],
        "values": [float(x) for x in monthly.tolist()],
    }


def build_signal_backtest_report(
    primary_df: pd.DataFrame,
    lump_sum_df: pd.DataFrame,
    idle_cash_df: pd.DataFrame,
    *,
    params: dict[str, Any],
    visualization: VisualizationMode = "series",
    annual_rf_rate: float = 0.05,
    primary_key: str = "ma_crossover",
    primary_label: str = "MA Crossover",
) -> dict[str, Any]:
    buys = int(primary_df["Buy_Fill"].sum()) if "Buy_Fill" in primary_df.columns else 0
    sells = int(primary_df["Sell_Fill"].sum()) if "Sell_Fill" in primary_df.columns else 0
    report: dict[str, Any] = {
        "params": params,
        "metrics": {
            primary_key: _metrics(
                primary_label, primary_df, annual_rf_rate=annual_rf_rate, buys=buys, sells=sells
            ),
            "lump_sum": _metrics("Lump Sum", lump_sum_df, annual_rf_rate=annual_rf_rate),
            "idle_cash": _metrics("Idle Cash", idle_cash_df, annual_rf_rate=annual_rf_rate),
        },
        "effective_start_date": primary_df.index[0].strftime("%Y-%m-%d"),
        "effective_end_date": primary_df.index[-1].strftime("%Y-%m-%d"),
        "series": None,
        "images": None,
    }
    if visualization in ("series", "both"):
        dates = [d.strftime("%Y-%m-%d") for d in primary_df.index]
        report["series"] = {
            "dates": dates,
            "portfolio_value": {
                primary_key: [float(x) for x in primary_df["Portfolio_Value"].tolist()],
                "lump_sum": [float(x) for x in lump_sum_df["Portfolio_Value"].tolist()],
                "idle_cash": [float(x) for x in idle_cash_df["Portfolio_Value"].tolist()],
            },
            "drawdown_pct": {
                primary_key: _drawdown_series(primary_df["Portfolio_Value"]),
                "lump_sum": _drawdown_series(lump_sum_df["Portfolio_Value"]),
                "idle_cash": _drawdown_series(idle_cash_df["Portfolio_Value"]),
            },
            "monthly_growth_pct": {
                primary_key: _monthly_growth(primary_df["Portfolio_Value"]),
                "lump_sum": _monthly_growth(lump_sum_df["Portfolio_Value"]),
                "idle_cash": _monthly_growth(idle_cash_df["Portfolio_Value"]),
            },
            "dip_buys": {"dates": [], "portfolio_values": []},
        }
    # ponytail: images/both skip raster plots for signal strategies (no shared plot API yet).
    # Ceiling: UI requesting images gets series only. Upgrade: parameterize DCA plots.
    return report
```

Export `build_signal_backtest_report` from `app/services/signals/__init__.py`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_signal_report.py tests/test_ma_crossover.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/signals/report.py app/services/signals/__init__.py tests/test_signal_report.py
git commit -m "$(cat <<'EOF'
Add signal backtest report builder for MA crossover.

EOF
)"
```

---

### Task 3: API schema, service persist, route

**Files:**
- Modify: `app/api/schemas/backtest.py`
- Modify: `tests/test_backtest_request.py`
- Modify: `app/services/backtest_service.py`
- Modify: `app/api/routes/backtest.py`

**Interfaces:**
- Produces:
  - `MaCrossoverRequest` with fields: `ticker`, `start_date`, `end_date`, `ma_type: Literal["sma","ema"] = "sma"`, `fast: int = 50` (ge=1), `slow: int = 200` (ge=2), `initial_cash`, `fee_rate`, `visualization`
  - model validator: `fast < slow`
  - `StrategyMetrics.buys_triggered: int | None = None`, `sells_triggered: int | None = None`
  - `run_and_persist_ma_crossover(db, *, start_date, end_date, ticker=None, ma_type="sma", fast=50, slow=200, initial_cash=None, fee_rate=None, visualization="series", settings=None, provider=None) -> BacktestRun`
  - Route `POST /ma-crossover`

- [ ] **Step 1: Write schema tests**

Add to `tests/test_backtest_request.py`:

```python
from app.api.schemas.backtest import MaCrossoverRequest


def test_ma_crossover_defaults() -> None:
    body = MaCrossoverRequest(start_date="2020-01-01", end_date="2021-01-01")
    assert body.ma_type == "sma"
    assert body.fast == 50
    assert body.slow == 200


def test_ma_crossover_fast_ge_slow_rejected() -> None:
    with pytest.raises(ValidationError):
        MaCrossoverRequest(
            start_date="2020-01-01",
            end_date="2021-01-01",
            fast=200,
            slow=50,
        )


def test_ma_crossover_invalid_ma_type_rejected() -> None:
    with pytest.raises(ValidationError):
        MaCrossoverRequest(
            start_date="2020-01-01",
            end_date="2021-01-01",
            ma_type="wma",  # type: ignore[arg-type]
        )
```

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/test_backtest_request.py -v`  
Expected: FAIL on missing `MaCrossoverRequest`

- [ ] **Step 3: Add schema**

In `app/api/schemas/backtest.py`, add:

```python
from pydantic import BaseModel, Field, field_validator, model_validator

class MaCrossoverRequest(BaseModel):
    ticker: str | None = None
    start_date: date
    end_date: date
    ma_type: Literal["sma", "ema"] = "sma"
    fast: int = Field(default=50, ge=1)
    slow: int = Field(default=200, ge=2)
    visualization: VisualizationMode = VisualizationMode.series
    initial_cash: float | None = None
    fee_rate: float | None = Field(default=None, ge=0, lt=1)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _coerce_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str) and "T" in value:
            return date.fromisoformat(value.split("T", 1)[0])
        return value

    @model_validator(mode="after")
    def _fast_lt_slow(self) -> MaCrossoverRequest:
        if self.fast >= self.slow:
            raise ValueError("fast must be less than slow")
        return self
```

Extend `StrategyMetrics`:

```python
class StrategyMetrics(BaseModel):
    # ...existing fields...
    dip_buys_triggered: int | None = None
    buys_triggered: int | None = None
    sells_triggered: int | None = None
```

- [ ] **Step 4: Implement service + route**

Add to `app/services/backtest_service.py`:

```python
from app.services.signals.ma_crossover import (
    run_idle_cash_baseline,
    run_lump_sum_baseline,
    run_ma_crossover,
)
from app.services.signals.report import build_signal_backtest_report


def run_and_persist_ma_crossover(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    ticker: str | None = None,
    ma_type: str = "sma",
    fast: int = 50,
    slow: int = 200,
    initial_cash: float | None = None,
    fee_rate: float | None = None,
    visualization: VisualizationMode = "series",
    settings: Settings | None = None,
    provider: MarketDataProvider | None = None,
) -> BacktestRun:
    settings = settings or get_settings()
    provider = provider or get_market_data_provider(settings)
    symbol = ticker or settings.default_ticker
    cash0 = initial_cash if initial_cash is not None else settings.default_initial_cash
    fee = fee_rate if fee_rate is not None else settings.default_fee_rate
    rf = settings.annual_rf_rate

    try:
        df = fetch_data(
            symbol,
            start_date.isoformat(),
            end_date.isoformat(),
            provider=provider,
        )
    except MarketDataError as exc:
        raise BacktestServiceError(str(exc)) from exc
    except Exception as exc:
        raise BacktestServiceError(f"Failed to fetch market data: {exc}") from exc

    if df.empty:
        raise BacktestServiceError(f"No market data for {symbol} in the requested range.")

    params: dict[str, Any] = {
        "ma_type": ma_type,
        "fast": fast,
        "slow": slow,
        "initial_cash": cash0,
        "fee_rate": fee,
    }
    try:
        primary_df, _ = run_ma_crossover(
            df,
            ma_type=ma_type,
            fast=fast,
            slow=slow,
            initial_cash=cash0,
            fee_rate=fee,
            annual_rf_rate=rf,
        )
    except ValueError as exc:
        raise BacktestServiceError(str(exc)) from exc

    if primary_df is None or primary_df.empty:
        raise BacktestServiceError("Test period too small after indicator warmup.")

    lump_df = run_lump_sum_baseline(primary_df, initial_cash=cash0, fee_rate=fee)
    idle_df = run_idle_cash_baseline(primary_df, initial_cash=cash0)
    report = build_signal_backtest_report(
        primary_df,
        lump_df,
        idle_df,
        params=params,
        visualization=visualization,
        annual_rf_rate=rf,
    )
    metrics = report["metrics"]["ma_crossover"]
    row = BacktestRun(
        ticker=symbol,
        strategy="ma_crossover",
        start_date=start_date,
        end_date=end_date,
        sharpe=metrics["sharpe_ratio"],
        cagr=metrics["cagr_pct"],
        total_return_pct=metrics["total_return_pct"],
        max_drawdown_pct=metrics["max_drawdown_pct"],
        visualization=visualization,
        params=params,
        result=report,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
```

(Match existing `BacktestRun` field names exactly — read `app/models/backtest_run.py` and mirror the DCA persist block.)

In `app/api/routes/backtest.py`:

```python
from app.api.schemas.backtest import MaCrossoverRequest
from app.services.backtest_service import run_and_persist_ma_crossover

@router.post("/ma-crossover", response_model=BacktestReport)
def create_ma_crossover_backtest(
    body: MaCrossoverRequest, db: Session = Depends(get_db)
) -> BacktestReport:
    if body.end_date < body.start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
    try:
        row = run_and_persist_ma_crossover(
            db,
            ticker=body.ticker,
            start_date=body.start_date,
            end_date=body.end_date,
            ma_type=body.ma_type,
            fast=body.fast,
            slow=body.slow,
            initial_cash=body.initial_cash,
            fee_rate=body.fee_rate,
            visualization=body.visualization.value,
        )
    except BacktestServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {exc}") from exc
    return _to_report(row)
```

- [ ] **Step 5: Run schema tests**

Run: `pytest tests/test_backtest_request.py tests/test_ma_crossover.py tests/test_signal_report.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/api/schemas/backtest.py app/services/backtest_service.py app/api/routes/backtest.py tests/test_backtest_request.py
git commit -m "$(cat <<'EOF'
Add MA crossover backtest API and persistence.

EOF
)"
```

---

### Task 4: Frontend types, store, form, charts

**Files:**
- Modify: `frontend/app/types/api.ts`
- Modify: `frontend/app/stores/backtest.ts`
- Modify: `frontend/app/components/backtest/BacktestForm.vue`
- Modify: `frontend/app/components/backtest/MetricsCards.vue`
- Modify: `frontend/app/components/charts/BacktestSeriesChart.vue`
- Modify: `frontend/app/pages/backtest/index.vue`

**Interfaces:**
- `MaCrossoverRequest` type + extend form union / shared form fields
- `StrategyMetrics` gains `buys_triggered?`, `sells_triggered?`
- `BacktestSeries.portfolio_value` gains optional `ma_crossover?`, `idle_cash?`; `standard_dca` becomes optional
- Store `runBacktest()` routes to `/dca` or `/ma-crossover` by strategy

- [ ] **Step 1: Update `frontend/app/types/api.ts`**

```typescript
export interface MaCrossoverRequest {
  ticker?: string | null
  start_date: string
  end_date: string
  ma_type?: 'sma' | 'ema'
  fast?: number | null
  slow?: number | null
  visualization?: VisualizationMode
  initial_cash?: number | null
  fee_rate?: number | null
}

export interface BacktestRequest {
  ticker?: string | null
  start_date: string
  end_date: string
  strategy?: 'aggressive_dca' | 'scheduled_dca' | 'ma_crossover'
  cadence?: 'weekly' | 'biweekly' | 'monthly'
  day_of_month?: number | null
  weekday?: number | null
  skip_after_buy_n?: number | null
  optimize?: boolean
  visualization?: VisualizationMode
  lookback?: number | null
  drawdown_thresh?: number | null
  sma_period?: number | null
  initial_cash?: number | null
  monthly_cash?: number | null
  fee_rate?: number | null
  ma_type?: 'sma' | 'ema'
  fast?: number | null
  slow?: number | null
}

export interface StrategyMetrics {
  total_cash_injected: number
  final_portfolio_value: number
  total_return_pct: number
  cagr_pct: number
  max_drawdown_pct: number
  sharpe_ratio: number
  dip_buys_triggered?: number | null
  buys_triggered?: number | null
  sells_triggered?: number | null
}

export interface BacktestSeries {
  dates: string[]
  portfolio_value: {
    aggressive_dca?: number[]
    scheduled_dca?: number[]
    ma_crossover?: number[]
    standard_dca?: number[]
    lump_sum: number[]
    idle_cash?: number[]
  }
  drawdown_pct: {
    aggressive_dca?: number[]
    scheduled_dca?: number[]
    ma_crossover?: number[]
    standard_dca?: number[]
    lump_sum: number[]
    idle_cash?: number[]
  }
  monthly_growth_pct?: Record<string, { dates: string[]; values: number[] }>
  dip_buys?: { dates: string[]; portfolio_values: number[] }
}
```

- [ ] **Step 2: Update store**

In `frontend/app/stores/backtest.ts`, extend form defaults:

```typescript
ma_type: 'sma',
fast: 50,
slow: 200,
```

Replace `runDca` with (keep `runDca` as alias if referenced):

```typescript
async function runBacktest(payload?: Partial<BacktestRequest>) {
  const { apiFetch, errorMessage } = useApi()
  pending.value = true
  error.value = null
  try {
    const body = { ...form, ...payload, visualization: 'series' as const }
    const path =
      body.strategy === 'ma_crossover'
        ? '/api/v1/backtest/ma-crossover'
        : '/api/v1/backtest/dca'
    const apiBody =
      body.strategy === 'ma_crossover'
        ? {
            ticker: body.ticker,
            start_date: body.start_date,
            end_date: body.end_date,
            ma_type: body.ma_type ?? 'sma',
            fast: body.fast ?? 50,
            slow: body.slow ?? 200,
            initial_cash: body.initial_cash,
            fee_rate: body.fee_rate,
            visualization: body.visualization,
          }
        : body
    lastReport.value = await apiFetch<BacktestReport>(path, {
      method: 'POST',
      body: apiBody,
    })
    return lastReport.value
  } catch (err) {
    error.value = errorMessage(err, 'Backtest failed')
    throw err
  } finally {
    pending.value = false
  }
}

async function runDca(payload?: Partial<BacktestRequest>) {
  return runBacktest(payload)
}
```

Export `runBacktest`.

- [ ] **Step 3: Update `BacktestForm.vue`**

- Add strategy item `{ title: 'MA Crossover', value: 'ma_crossover' }`
- `isMa = strategy === 'ma_crossover'`
- `isAggressive = strategy === 'aggressive_dca'`
- `isScheduled = strategy === 'scheduled_dca'`
- Show MA fields when `isMa`: ma_type select, fast/slow number fields
- Hide monthly cash / cadence / optimize / dip params when `isMa`
- Keep initial_cash + fee + dates for MA

- [ ] **Step 4: Update MetricsCards + chart + page copy**

`MetricsCards.vue` labels:

```typescript
ma_crossover: 'MA Crossover',
idle_cash: 'Idle Cash',
```

Show buys/sells when present:

```vue
<template v-if="card.buys != null">
  <dt>Buys</dt><dd>{{ card.buys }}</dd>
</template>
<template v-if="card.sells != null">
  <dt>Sells</dt><dd>{{ card.sells }}</dd>
</template>
```

Map from `m.buys_triggered` / `m.sells_triggered`.

`BacktestSeriesChart.vue` primary key detection:

```typescript
const primaryKey = computed(() => {
  const pv = props.series.portfolio_value
  if (pv.ma_crossover != null) return 'ma_crossover'
  if (pv.scheduled_dca != null) return 'scheduled_dca'
  return 'aggressive_dca'
})
const primaryName = computed(() =>
  ({
    ma_crossover: 'MA Crossover',
    scheduled_dca: 'Scheduled DCA',
    aggressive_dca: 'Aggressive DCA',
  } as Record<string, string>)[primaryKey.value],
)
```

Build `seriesList` baselines:

- If `ma_crossover`: lines for primary, Lump Sum, Idle Cash (skip Standard DCA)
- Else: existing primary + Standard DCA + Lump Sum

`index.vue`: broaden title/description to “Backtest” (not only DCA); call `store.runBacktest()` (or keep `runDca` alias).

- [ ] **Step 5: Smoke-check**

Run backend tests: `pytest tests/test_ma_crossover.py tests/test_signal_report.py tests/test_backtest_request.py -v`  
Expected: PASS

Optionally hit `POST /api/v1/backtest/ma-crossover` with a known ticker if server/provider available.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/types/api.ts frontend/app/stores/backtest.ts \
  frontend/app/components/backtest/BacktestForm.vue \
  frontend/app/components/backtest/MetricsCards.vue \
  frontend/app/components/charts/BacktestSeriesChart.vue \
  frontend/app/pages/backtest/index.vue
git commit -m "$(cat <<'EOF'
Add MA crossover strategy to the backtest UI.

EOF
)"
```

---

## Plan self-review

**Spec coverage:** Engine rules, baselines, API, persistence, frontend, errors, and one synthetic test each have tasks (1–4).

**Placeholders:** None intentional; images deferred with explicit ponytail note in Task 2.

**Type consistency:** `ma_crossover` / `sma`|`ema` / `buys_triggered` / `sells_triggered` / next-open fills used consistently across tasks.
