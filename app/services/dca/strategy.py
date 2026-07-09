from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.dca.metrics import calculate_sharpe


def run_aggressive_dca(
    df: pd.DataFrame,
    lookback: int = 100,
    drawdown_thresh: float = 0.15,
    sma_period: int = 200,
    initial_cash: float = 10_000_000,
    monthly_cash: float = 1_000_000,
    fee_rate: float = 0.0015,
    annual_rf_rate: float = 0.05,
) -> tuple[pd.DataFrame, float]:
    """
    Aggressive DCA (Structural Drawdown):
    - Day 1: Deploys Initial Cash
    - 1st of every month: Deploys 1x Monthly Cash
    - On Dip Signal: Deploys 2x Monthly Cash immediately.
      Dip = price dropping X% below the N-day rolling high, while > SMA.
    """
    data = df.copy()

    data["SMA"] = data["Close"].rolling(window=sma_period).mean()
    data["Rolling_High"] = data["High"].rolling(window=lookback).max()
    data["Drawdown_From_High"] = (data["Close"] - data["Rolling_High"]) / data["Rolling_High"]

    data["Condition_Met"] = (data["Drawdown_From_High"] <= -drawdown_thresh) & (
        data["Close"] > data["SMA"]
    )
    data["Raw_Execution_Signal"] = data["Condition_Met"].shift(1).fillna(False)

    test_data = data.dropna(subset=["SMA", "Rolling_High"]).copy()
    if test_data.empty:
        return test_data, 0.0

    test_data["YearMonth"] = test_data.index.to_period("M")

    first_days = test_data.groupby("YearMonth").head(1).index
    test_data["Is_First_Day"] = False
    test_data.loc[first_days, "Is_First_Day"] = True

    test_data["Is_Dip_Day"] = test_data["Raw_Execution_Signal"]
    test_data["Execution_Signal"] = test_data["Is_Dip_Day"]

    test_data["Cash_Injected_Today"] = np.where(test_data["Is_First_Day"], monthly_cash, 0.0)
    test_data.iloc[0, test_data.columns.get_loc("Cash_Injected_Today")] = initial_cash

    test_data["Cash_Injected_Today"] = np.where(
        test_data["Is_Dip_Day"],
        test_data["Cash_Injected_Today"] + (monthly_cash * 2),
        test_data["Cash_Injected_Today"],
    )

    test_data["Shares_Bought"] = (test_data["Cash_Injected_Today"] * (1 - fee_rate)) / test_data[
        "Open"
    ]
    test_data["Total_Shares"] = test_data["Shares_Bought"].cumsum()
    test_data["Portfolio_Value"] = test_data["Total_Shares"] * test_data["Close"]
    test_data["Total_Cash_Deployed"] = test_data["Cash_Injected_Today"].cumsum()

    prev_value = test_data["Portfolio_Value"].shift(1)
    test_data["Strategy_Return"] = (
        test_data["Portfolio_Value"] - test_data["Cash_Injected_Today"] - prev_value
    ) / prev_value
    test_data["Strategy_Return"] = test_data["Strategy_Return"].fillna(0)

    sharpe_ratio = calculate_sharpe(test_data["Strategy_Return"], annual_rf_rate=annual_rf_rate)
    return test_data, sharpe_ratio


def run_standard_dca(test_data_from_strategy: pd.DataFrame, fee_rate: float = 0.0015) -> pd.DataFrame:
    """Equilibrated Baseline: Divides total cash equally across all months."""
    dca = pd.DataFrame(index=test_data_from_strategy.index)
    dca["Open"] = test_data_from_strategy["Open"]
    dca["Close"] = test_data_from_strategy["Close"]

    final_total_cash = test_data_from_strategy["Total_Cash_Deployed"].iloc[-1]

    dca["YearMonth"] = dca.index.to_period("M")
    first_days = dca.groupby("YearMonth").head(1).index
    num_months = len(first_days)
    equal_monthly_cash = final_total_cash / num_months

    dca["Is_First_Day"] = False
    dca.loc[first_days, "Is_First_Day"] = True

    dca["Cash_Injected_Today"] = np.where(dca["Is_First_Day"], equal_monthly_cash, 0.0)

    dca["Shares_Bought"] = (dca["Cash_Injected_Today"] * (1 - fee_rate)) / dca["Open"]
    dca["Total_Shares"] = dca["Shares_Bought"].cumsum()
    dca["Portfolio_Value"] = dca["Total_Shares"] * dca["Close"]
    dca["Total_Cash_Deployed"] = dca["Cash_Injected_Today"].cumsum()

    prev_value = dca["Portfolio_Value"].shift(1)
    dca["Strategy_Return"] = (
        dca["Portfolio_Value"] - dca["Cash_Injected_Today"] - prev_value
    ) / prev_value
    dca["Strategy_Return"] = dca["Strategy_Return"].fillna(0)

    return dca


def run_benchmark(test_data_from_strategy: pd.DataFrame, fee_rate: float = 0.0015) -> pd.DataFrame:
    """Lump Sum: Deploys all cash used by Aggressive DCA on Day 1."""
    benchmark = pd.DataFrame(index=test_data_from_strategy.index)
    benchmark["Close"] = test_data_from_strategy["Close"]

    total_cash_deployed = test_data_from_strategy["Total_Cash_Deployed"].iloc[-1]
    initial_price = test_data_from_strategy["Open"].iloc[0]

    total_shares = (total_cash_deployed * (1 - fee_rate)) / initial_price
    benchmark["Portfolio_Value"] = total_shares * benchmark["Close"]
    benchmark["Strategy_Return"] = benchmark["Portfolio_Value"].pct_change().fillna(0)
    benchmark["Total_Cash_Deployed"] = total_cash_deployed

    return benchmark
