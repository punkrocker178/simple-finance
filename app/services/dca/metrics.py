from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_sharpe(portfolio_returns: pd.Series, annual_rf_rate: float = 0.05) -> float:
    daily_rf = (1 + annual_rf_rate) ** (1 / 252) - 1
    excess_returns = portfolio_returns - daily_rf
    if len(excess_returns) < 2 or excess_returns.std() == 0:
        return 0.0
    return float(np.sqrt(252) * (excess_returns.mean() / excess_returns.std()))


def calculate_cagr(total_return_pct: float, days: int) -> float:
    if days <= 0:
        return 0.0
    years = days / 365.25
    return float(((1 + total_return_pct / 100) ** (1 / years) - 1) * 100)
