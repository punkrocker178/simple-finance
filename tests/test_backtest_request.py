"""Backtest request validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas.backtest import BacktestRequest


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
