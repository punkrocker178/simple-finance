from __future__ import annotations

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
