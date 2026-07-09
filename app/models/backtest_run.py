from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.db import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (
        Index("ix_backtest_runs_ticker", "ticker"),
        Index("ix_backtest_runs_strategy", "strategy"),
        Index("ix_backtest_runs_ticker_strategy", "ticker", "strategy"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False, default="aggressive_dca")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    cagr: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    visualization: Mapped[str] = mapped_column(String(16), nullable=False, default="series")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
