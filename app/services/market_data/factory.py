from __future__ import annotations

from typing import Protocol

import pandas as pd

from app.core.config import Settings, get_settings
from app.services.market_data.base import MarketDataProvider
from app.services.market_data.http_provider import HttpProvider
from app.services.market_data.vnstock_client import VnstockClient
from app.services.market_data.vnstock_provider import VnstockProvider
from app.services.market_data.yfinance_client import YFinanceClient
from app.services.market_data.yfinance_provider import YFinanceProvider


class MarketDataClient(Protocol):
    def get_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        *,
        length: str | int | None = None,
    ) -> pd.DataFrame: ...

    def get_ticker_info(self, ticker: str) -> dict: ...

    def get_fast_info(self, ticker: str) -> dict: ...

    def search_vn_tickers(self, query: str, limit: int = 20) -> list[dict]: ...

    def get_market_summary(self, symbols: list[str]) -> list[dict]: ...

    @staticmethod
    def ohlcv_to_records(df: pd.DataFrame) -> list[dict]: ...


def get_market_data_provider(settings: Settings | None = None) -> MarketDataProvider:
    settings = settings or get_settings()
    provider = settings.market_data_provider.lower().strip()
    if provider == "http":
        return HttpProvider(settings)
    if provider == "yfinance":
        return YFinanceProvider()
    if provider == "vnstock":
        return VnstockProvider()
    raise ValueError(f"Unsupported market_data_provider: {settings.market_data_provider}")


def get_market_data_client(settings: Settings | None = None, provider: str | None = None) -> MarketDataClient:
    settings = settings or get_settings()
    provider = provider or settings.market_data_provider.lower().strip()
    if provider == "yfinance":
        return YFinanceClient()
    if provider == "vnstock":
        return VnstockClient()
    if provider == "http":
        raise ValueError(
            "MARKET_DATA_PROVIDER=http only supports OHLCV backtests; "
            "use yfinance or vnstock for market API routes."
        )
    raise ValueError(f"Unsupported market_data_provider: {settings.market_data_provider}")
