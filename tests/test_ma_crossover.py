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
    # First post-warmup bar needs Open == Close so lump-sum day-0 PV equals initial_cash.
    df = _ohlcv_from_close([100.0, 110.0, 110.0, 95.0])
    primary, _ = run_ma_crossover(df, fast=2, slow=3, initial_cash=1_000.0, fee_rate=0.0)
    lump = run_lump_sum_baseline(primary, initial_cash=1_000.0, fee_rate=0.0)
    idle = run_idle_cash_baseline(primary, initial_cash=1_000.0)
    assert lump["Portfolio_Value"].iloc[0] == pytest.approx(1_000.0)
    assert idle["Portfolio_Value"].iloc[-1] == pytest.approx(1_000.0)
    assert (idle["Strategy_Return"] == 0).all()
