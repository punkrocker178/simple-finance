"""Scheduled DCA injection mask and cash simulation."""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.dca.scheduled import build_injection_mask, run_scheduled_dca


def _bday_ohlcv(start: str, periods: int) -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=periods)
    close = pd.Series(100.0, index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close},
        index=idx,
    )


def test_monthly_skip_and_next_trading_day_roll() -> None:
    # Jan 1 2021 is Friday New Year — not a business day; first bday is Jan 4.
    df = _bday_ohlcv("2021-01-04", periods=80)
    mask = build_injection_mask(
        df.index,
        cadence="monthly",
        day_of_month=1,
        skip_after_buy_n=1,
    )
    # Day-1 (Jan 4) excluded from skip bookkeeping; schedule starts Feb onward.
    # skip_after_buy_n=1 → keep Feb, skip Mar, keep Apr, ...
    fired = list(df.index[mask])
    assert pd.Timestamp("2021-01-04") not in fired
    assert fired[0] == pd.Timestamp("2021-02-01")
    assert pd.Timestamp("2021-03-01") not in fired
    assert fired[1] == pd.Timestamp("2021-04-01")


def test_run_scheduled_dca_day1_initial_only_no_double_inject() -> None:
    df = _bday_ohlcv("2021-01-04", periods=40)
    out, sharpe = run_scheduled_dca(
        df,
        initial_cash=10_000_000,
        monthly_cash=1_000_000,
        cadence="monthly",
        day_of_month=1,
        skip_after_buy_n=0,
    )
    assert out.iloc[0]["Cash_Injected_Today"] == 10_000_000
    # First schedule day coincides with day-1 → still initial only
    assert bool(out.iloc[0]["Is_Schedule_Day"]) is False
    assert out["Execution_Signal"].sum() == 0
    assert out["Total_Cash_Deployed"].iloc[-1] > 10_000_000
    assert isinstance(sharpe, float)


def test_gappy_index_skips_phantom_period_before_skip_n() -> None:
    # February missing: Feb 1 would roll to Mar 1 — same as Mar target; must not
    # count as an extra period or skip_after_buy_n alternation shifts.
    jan = pd.bdate_range("2021-01-04", "2021-01-29")
    mar = pd.bdate_range("2021-03-01", periods=80)
    idx = jan.append(mar)
    close = pd.Series(100.0, index=idx)
    df = pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close},
        index=idx,
    )
    mask = build_injection_mask(
        df.index,
        cadence="monthly",
        day_of_month=1,
        skip_after_buy_n=1,
    )
    fired = list(df.index[mask])
    # Day-1 dropped; Feb rolls to Mar (deduped) — keep Mar, skip Apr, keep May.
    assert pd.Timestamp("2021-01-04") not in fired
    assert fired[0] == pd.Timestamp("2021-03-01")
    assert fired[1] == pd.Timestamp("2021-05-03")  # May 1 2021 is Saturday → May 3
    assert pd.Timestamp("2021-04-01") not in fired


def test_run_scheduled_dca_skip_after_buy_excludes_day1_from_phase() -> None:
    """skip_after_buy_n alternates from first post-day-1 schedule hit, not day-1 coincident."""
    # Index starts 2021-01-04 (day-1 initial). day_of_month=1, skip_after_buy_n=1.
    df = _bday_ohlcv("2021-01-04", periods=120)
    out, _ = run_scheduled_dca(
        df,
        cadence="monthly",
        day_of_month=1,
        skip_after_buy_n=1,
    )
    assert bool(out.iloc[0]["Is_Schedule_Day"]) is False
    schedule_days = out.index[out["Is_Schedule_Day"]]
    # Feb kept, Mar skipped, Apr kept, May skipped, Jun kept, ...
    assert schedule_days[0] == pd.Timestamp("2021-02-01")
    assert pd.Timestamp("2021-03-01") not in schedule_days
    assert schedule_days[1] == pd.Timestamp("2021-04-01")
    assert pd.Timestamp("2021-05-03") not in schedule_days  # May 1 is Sat → May 3 bday
    assert schedule_days[2] == pd.Timestamp("2021-06-01")


def test_no_schedule_days_raises() -> None:
    df = _bday_ohlcv("2021-01-04", periods=2)
    with pytest.raises(ValueError, match="No scheduled injection"):
        run_scheduled_dca(df, cadence="monthly", day_of_month=1)
