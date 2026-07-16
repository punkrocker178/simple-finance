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
    signals = report["series"]["trade_signals"]
    assert len(signals["buys"]["dates"]) == m["buys_triggered"]
    assert len(signals["sells"]["dates"]) == m["sells_triggered"]
    if signals["buys"]["dates"]:
        assert signals["buys"]["dates"][0] == primary.index[primary["Buy_Fill"]][0].strftime(
            "%Y-%m-%d"
        )
