from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from app.services.dca.metrics import calculate_cagr, calculate_sharpe
from app.services.dca.plots import render_performance_image

VisualizationMode = Literal["series", "images", "both"]


def _strategy_metrics(
    name: str,
    df: pd.DataFrame,
    annual_rf_rate: float = 0.05,
) -> dict[str, Any]:
    total_cash_in = float(df["Total_Cash_Deployed"].iloc[-1])
    final_val = float(df["Portfolio_Value"].iloc[-1])
    ret = ((final_val / total_cash_in) - 1) * 100
    days = (df.index[-1] - df.index[0]).days
    cagr = calculate_cagr(ret, days)
    peak = df["Portfolio_Value"].cummax()
    dd = float(((df["Portfolio_Value"] - peak) / peak).min() * 100)
    sharpe = calculate_sharpe(df["Strategy_Return"], annual_rf_rate=annual_rf_rate)

    executions: int | None
    if name == "Aggressive DCA":
        executions = int(df["Execution_Signal"].sum())
    else:
        executions = None

    return {
        "total_cash_injected": total_cash_in,
        "final_portfolio_value": final_val,
        "total_return_pct": float(ret),
        "cagr_pct": float(cagr),
        "max_drawdown_pct": dd,
        "sharpe_ratio": float(sharpe),
        "dip_buys_triggered": executions,
    }


def build_metrics(
    agg_dca_df: pd.DataFrame,
    std_dca_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    annual_rf_rate: float = 0.05,
) -> dict[str, dict[str, Any]]:
    frames = {
        "aggressive_dca": ("Aggressive DCA", agg_dca_df),
        "standard_dca": ("Standard DCA", std_dca_df),
        "lump_sum": ("Lump Sum Benchmark", benchmark_df),
    }
    return {
        key: _strategy_metrics(label, frame, annual_rf_rate=annual_rf_rate)
        for key, (label, frame) in frames.items()
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


def build_series(
    agg_dca_df: pd.DataFrame,
    std_dca_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
) -> dict[str, Any]:
    dates = [d.strftime("%Y-%m-%d") for d in agg_dca_df.index]
    dip_mask = agg_dca_df["Execution_Signal"].astype(bool)
    dip_dates = [d.strftime("%Y-%m-%d") for d in agg_dca_df.index[dip_mask]]
    dip_values = [float(x) for x in agg_dca_df.loc[dip_mask, "Portfolio_Value"].tolist()]

    return {
        "dates": dates,
        "portfolio_value": {
            "aggressive_dca": [float(x) for x in agg_dca_df["Portfolio_Value"].tolist()],
            "standard_dca": [float(x) for x in std_dca_df["Portfolio_Value"].tolist()],
            "lump_sum": [float(x) for x in benchmark_df["Portfolio_Value"].tolist()],
        },
        "drawdown_pct": {
            "aggressive_dca": _drawdown_series(agg_dca_df["Portfolio_Value"]),
            "standard_dca": _drawdown_series(std_dca_df["Portfolio_Value"]),
            "lump_sum": _drawdown_series(benchmark_df["Portfolio_Value"]),
        },
        "monthly_growth_pct": {
            "aggressive_dca": _monthly_growth(agg_dca_df["Portfolio_Value"]),
            "standard_dca": _monthly_growth(std_dca_df["Portfolio_Value"]),
            "lump_sum": _monthly_growth(benchmark_df["Portfolio_Value"]),
        },
        "dip_buys": {"dates": dip_dates, "portfolio_values": dip_values},
    }


def build_backtest_report(
    agg_dca_df: pd.DataFrame,
    std_dca_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    params: dict[str, Any],
    visualization: VisualizationMode = "series",
    annual_rf_rate: float = 0.05,
    title_suffix: str = "",
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "params": params,
        "metrics": build_metrics(
            agg_dca_df, std_dca_df, benchmark_df, annual_rf_rate=annual_rf_rate
        ),
        "series": None,
        "images": None,
    }

    if visualization in ("series", "both"):
        report["series"] = build_series(agg_dca_df, std_dca_df, benchmark_df)

    if visualization in ("images", "both"):
        report["images"] = {
            "performance": render_performance_image(
                agg_dca_df, std_dca_df, benchmark_df, title_suffix=title_suffix
            )
        }

    return report
