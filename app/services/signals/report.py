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
