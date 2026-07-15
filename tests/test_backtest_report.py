"""Backtest report effective date metadata."""

from __future__ import annotations

import pandas as pd

from app.services.dca.report import build_backtest_report
from app.services.dca.scheduled import run_scheduled_dca
from app.services.dca.strategy import run_aggressive_dca, run_benchmark, run_standard_dca


def _sample_ohlcv(rows: int = 260) -> pd.DataFrame:
    idx = pd.bdate_range("2020-01-01", periods=rows)
    close = pd.Series(range(100, 100 + rows), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
        },
        index=idx,
    )


def test_build_backtest_report_includes_effective_dates() -> None:
    df = _sample_ohlcv()
    agg_df, _ = run_aggressive_dca(df, lookback=50, sma_period=100)
    std_df = run_standard_dca(agg_df)
    bench_df = run_benchmark(agg_df)

    report = build_backtest_report(agg_df, std_df, bench_df, params={"optimized": False})

    assert report["effective_start_date"] == agg_df.index[0].strftime("%Y-%m-%d")
    assert report["effective_end_date"] == agg_df.index[-1].strftime("%Y-%m-%d")
    assert report["series"]["dates"][0] == report["effective_start_date"]
    assert report["series"]["dates"][-1] == report["effective_end_date"]


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
