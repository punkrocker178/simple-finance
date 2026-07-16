"""Backtest request validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas.backtest import BacktestRequest, MaCrossoverRequest


def test_fee_rate_must_be_fraction_not_percent() -> None:
    with pytest.raises(ValidationError) as exc:
        BacktestRequest(
            ticker="FUEVFVND.VN",
            start_date="2025-05-01",
            end_date="2026-05-01",
            fee_rate=1.5,
        )
    assert "fee_rate" in str(exc.value).lower()


def test_fee_rate_fraction_accepted() -> None:
    body = BacktestRequest(
        ticker="FUEVFVND.VN",
        start_date="2025-05-01",
        end_date="2026-05-01",
        fee_rate=0.015,
    )
    assert body.fee_rate == 0.015


def test_scheduled_strategy_defaults() -> None:
    body = BacktestRequest(
        start_date="2021-01-01",
        end_date="2022-01-01",
        strategy="scheduled_dca",
    )
    assert body.strategy == "scheduled_dca"
    assert body.cadence == "monthly"
    assert body.day_of_month == 1
    assert body.weekday == 0
    assert body.skip_after_buy_n == 0


def test_day_of_month_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        BacktestRequest(
            start_date="2021-01-01",
            end_date="2022-01-01",
            strategy="scheduled_dca",
            day_of_month=29,
        )


def test_weekday_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        BacktestRequest(
            start_date="2021-01-01",
            end_date="2022-01-01",
            strategy="scheduled_dca",
            weekday=5,
        )


def test_skip_after_buy_n_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        BacktestRequest(
            start_date="2021-01-01",
            end_date="2022-01-01",
            strategy="scheduled_dca",
            skip_after_buy_n=-1,
        )


def test_default_strategy_remains_aggressive() -> None:
    body = BacktestRequest(start_date="2021-01-01", end_date="2022-01-01")
    assert body.strategy == "aggressive_dca"


def test_ma_crossover_defaults() -> None:
    body = MaCrossoverRequest(start_date="2020-01-01", end_date="2021-01-01")
    assert body.ma_type == "sma"
    assert body.fast == 50
    assert body.slow == 200


def test_ma_crossover_fast_ge_slow_rejected() -> None:
    with pytest.raises(ValidationError):
        MaCrossoverRequest(
            start_date="2020-01-01",
            end_date="2021-01-01",
            fast=200,
            slow=50,
        )


def test_ma_crossover_invalid_ma_type_rejected() -> None:
    with pytest.raises(ValidationError):
        MaCrossoverRequest(
            start_date="2020-01-01",
            end_date="2021-01-01",
            ma_type="wma",  # type: ignore[arg-type]
        )
