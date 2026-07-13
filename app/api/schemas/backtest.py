from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class VisualizationMode(str, Enum):
    series = "series"
    images = "images"
    both = "both"


class BacktestRequest(BaseModel):
    ticker: str | None = None
    start_date: date
    end_date: date
    optimize: bool = True
    visualization: VisualizationMode = VisualizationMode.series
    lookback: int | None = None
    drawdown_thresh: float | None = None
    sma_period: int | None = None
    initial_cash: float | None = None
    monthly_cash: float | None = None
    fee_rate: float | None = Field(
        default=None,
        description="Trading fee as a fraction (e.g. 0.015 for 1.5%), not a percent.",
        ge=0,
        lt=1,
    )

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _coerce_date(cls, value: Any) -> Any:
        # Accept ISO datetimes from clients; store as calendar dates.
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str) and "T" in value:
            return date.fromisoformat(value.split("T", 1)[0])
        return value


class StrategyMetrics(BaseModel):
    total_cash_injected: float
    final_portfolio_value: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    dip_buys_triggered: int | None = None


class BacktestReport(BaseModel):
    id: UUID
    ticker: str
    strategy: str = "aggressive_dca"
    visualization: VisualizationMode
    start_date: date
    end_date: date
    effective_start_date: date | None = None
    effective_end_date: date | None = None
    params: dict[str, Any]
    metrics: dict[str, StrategyMetrics | dict[str, Any]]
    series: dict[str, Any] | None = None
    images: dict[str, Any] | None = None
    created_at: datetime | None = None


class BacktestRunSummary(BaseModel):
    id: UUID
    ticker: str
    strategy: str
    start_date: date
    end_date: date
    effective_start_date: date | None = None
    effective_end_date: date | None = None
    created_at: datetime
    sharpe: float | None = None
    cagr: float | None = None
    total_return_pct: float | None = None
    max_drawdown_pct: float | None = None
    visualization: Literal["series", "images", "both"] | str
    params: dict[str, Any] = Field(default_factory=dict)


class BacktestRunListResponse(BaseModel):
    items: list[BacktestRunSummary]
    count: int
