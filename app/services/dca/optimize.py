from __future__ import annotations

from itertools import product

import pandas as pd

from app.services.dca.strategy import run_aggressive_dca


def optimize_strategy(
    df: pd.DataFrame,
    train_fraction: float = 0.7,
    initial_cash: float = 10_000_000,
    monthly_cash: float = 1_000_000,
    fee_rate: float = 0.0015,
    annual_rf_rate: float = 0.05,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    split_idx = int(len(df) * train_fraction)
    in_sample_df = df.iloc[:split_idx]

    lookbacks = [50, 100, 150, 252]
    drawdowns = [0.05, 0.10, 0.15, 0.20]
    smas = [100, 150, 200]

    max_lookback = max(max(lookbacks), max(smas))
    out_of_sample_df = df.iloc[split_idx - max_lookback :]

    best_sharpe = float("-inf")
    best_params: dict = {}

    for lb, dd, sma in product(lookbacks, drawdowns, smas):
        if lb >= len(in_sample_df) or sma >= len(in_sample_df):
            continue

        _, sharpe = run_aggressive_dca(
            in_sample_df,
            lookback=lb,
            drawdown_thresh=dd,
            sma_period=sma,
            initial_cash=initial_cash,
            monthly_cash=monthly_cash,
            fee_rate=fee_rate,
            annual_rf_rate=annual_rf_rate,
        )
        if not pd.isna(sharpe) and sharpe > best_sharpe:
            best_sharpe = sharpe
            best_params = {"lookback": lb, "drawdown_thresh": dd, "sma_period": sma}

    if not best_params:
        best_params = {"lookback": 100, "drawdown_thresh": 0.10, "sma_period": 200}

    best_params["in_sample_sharpe"] = float(best_sharpe) if best_sharpe != float("-inf") else 0.0
    return best_params, in_sample_df, out_of_sample_df
