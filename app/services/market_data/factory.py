from __future__ import annotations

from app.core.config import Settings, get_settings
from app.services.market_data.base import MarketDataProvider
from app.services.market_data.http_provider import HttpProvider
from app.services.market_data.yfinance_provider import YFinanceProvider


def get_market_data_provider(settings: Settings | None = None) -> MarketDataProvider:
    settings = settings or get_settings()
    provider = settings.market_data_provider.lower().strip()
    if provider == "http":
        return HttpProvider(settings)
    if provider == "yfinance":
        return YFinanceProvider()
    raise ValueError(f"Unsupported market_data_provider: {settings.market_data_provider}")
