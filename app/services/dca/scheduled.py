from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.dca.metrics import calculate_sharpe

# ponytail: duplicates Aggressive cash/shares accounting and calendar injection.
# Ceiling: two strategies drift apart on fee/return formulas.
# Upgrade: extract schedule-mask generator + apply_cash_on_mask() shared by both.


def _next_trading_day(index: pd.DatetimeIndex, target: pd.Timestamp) -> pd.Timestamp | None:
    pos = index.searchsorted(target)
    if pos >= len(index):
        return None
    return index[pos]


def _monthly_targets(index: pd.DatetimeIndex, day_of_month: int) -> list[pd.Timestamp]:
    start = index[0].normalize()
    end = index[-1].normalize()
    targets: list[pd.Timestamp] = []
    cursor = pd.Timestamp(year=start.year, month=start.month, day=1)
    while cursor <= end:
        day = min(day_of_month, cursor.days_in_month)
        targets.append(pd.Timestamp(year=cursor.year, month=cursor.month, day=day))
        cursor = (cursor + pd.offsets.MonthBegin(1))
    return targets


def _weekly_targets(index: pd.DatetimeIndex, weekday: int) -> list[pd.Timestamp]:
    """One target per ISO week on the given weekday (0=Mon)."""
    start = index[0].normalize()
    end = index[-1].normalize()
    # Align to first date with that weekday on/after start's week Monday
    week_start = start - pd.Timedelta(days=start.weekday())
    targets: list[pd.Timestamp] = []
    cursor = week_start + pd.Timedelta(days=weekday)
    if cursor < start:
        cursor += pd.Timedelta(days=7)
    while cursor <= end + pd.Timedelta(days=7):
        targets.append(cursor)
        cursor += pd.Timedelta(days=7)
    return targets


def build_injection_mask(
    index: pd.DatetimeIndex,
    *,
    cadence: str,
    day_of_month: int = 1,
    weekday: int = 0,
    skip_after_buy_n: int = 0,
) -> pd.Series:
    if cadence == "monthly":
        raw = _monthly_targets(index, day_of_month)
    elif cadence in ("weekly", "biweekly"):
        raw = _weekly_targets(index, weekday)
    else:
        raise ValueError(f"Unsupported cadence: {cadence}")

    rolled: list[pd.Timestamp] = []
    for i, t in enumerate(raw):
        hit = _next_trading_day(index, t)
        if hit is None:
            continue
        next_raw = raw[i + 1] if i + 1 < len(raw) else None
        if next_raw is not None and hit >= next_raw:
            continue
        rolled.append(hit)

    # Dedupe while preserving order (roll collisions)
    seen: set[pd.Timestamp] = set()
    unique: list[pd.Timestamp] = []
    for h in rolled:
        if h not in seen:
            seen.add(h)
            unique.append(h)

    if cadence == "biweekly":
        unique = unique[::2]

    if skip_after_buy_n > 0:
        kept: list[pd.Timestamp] = []
        skip_left = 0
        for h in unique:
            if skip_left > 0:
                skip_left -= 1
                continue
            kept.append(h)
            skip_left = skip_after_buy_n
        unique = kept

    mask = pd.Series(False, index=index)
    for h in unique:
        mask.loc[h] = True
    return mask


def run_scheduled_dca(
    df: pd.DataFrame,
    *,
    initial_cash: float = 10_000_000,
    monthly_cash: float = 1_000_000,
    fee_rate: float = 0.0015,
    cadence: str = "monthly",
    day_of_month: int = 1,
    weekday: int = 0,
    skip_after_buy_n: int = 0,
    annual_rf_rate: float = 0.05,
) -> tuple[pd.DataFrame, float]:
    if df.empty:
        raise ValueError("No scheduled injection days in range.")

    data = df.copy()
    schedule = build_injection_mask(
        data.index,
        cadence=cadence,
        day_of_month=day_of_month,
        weekday=weekday,
        skip_after_buy_n=skip_after_buy_n,
    )
    # Day-1 initial overwrites schedule for position 0
    schedule.iloc[0] = False

    if not schedule.any():
        raise ValueError("No scheduled injection days in range.")

    data["Is_Schedule_Day"] = schedule
    data["Cash_Injected_Today"] = np.where(schedule, monthly_cash, 0.0)
    data.iloc[0, data.columns.get_loc("Cash_Injected_Today")] = initial_cash

    data["Shares_Bought"] = (data["Cash_Injected_Today"] * (1 - fee_rate)) / data["Open"]
    data["Total_Shares"] = data["Shares_Bought"].cumsum()
    data["Portfolio_Value"] = data["Total_Shares"] * data["Close"]
    data["Total_Cash_Deployed"] = data["Cash_Injected_Today"].cumsum()

    prev_value = data["Portfolio_Value"].shift(1)
    data["Strategy_Return"] = (
        data["Portfolio_Value"] - data["Cash_Injected_Today"] - prev_value
    ) / prev_value
    data["Strategy_Return"] = data["Strategy_Return"].fillna(0)
    data["Execution_Signal"] = False

    sharpe = calculate_sharpe(data["Strategy_Return"], annual_rf_rate=annual_rf_rate)
    return data, sharpe
