from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TickerInfoResponse(BaseModel):
    symbol: str
    shortName: str | None = None
    longName: str | None = None
    exchange: str | None = None
    quoteType: str | None = None
    currency: str | None = None
    market: str | None = None
    sector: str | None = None
    industry: str | None = None
    marketCap: float | None = None
    previousClose: float | None = None
    regularMarketPrice: float | None = None
    fiftyTwoWeekHigh: float | None = None
    fiftyTwoWeekLow: float | None = None
    trailingPE: float | None = None
    dividendYield: float | None = None
    volume: float | None = None
    averageVolume: float | None = None

    model_config = {"extra": "allow"}


class OhlcvBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float


class OhlcvResponse(BaseModel):
    ticker: str
    start: str
    end: str
    bars: list[OhlcvBar]


class MarketSummaryItem(BaseModel):
    symbol: str
    last_price: float | None = None
    previous_close: float | None = None
    open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    year_high: float | None = None
    year_low: float | None = None
    currency: str | None = None
    exchange: str | None = None
    market_cap: float | None = None
    error: str | None = None

    model_config = {"extra": "allow"}


class MarketSummaryResponse(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
