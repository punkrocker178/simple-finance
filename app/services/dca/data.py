from __future__ import annotations

import pandas as pd

from app.services.market_data.base import MarketDataProvider
from app.services.market_data.factory import get_market_data_provider


def fetch_data(
    ticker: str,
    start_date: str,
    end_date: str,
    provider: MarketDataProvider | None = None,
) -> pd.DataFrame:
    provider = provider or get_market_data_provider()
    return provider.get_ohlcv(ticker, start_date, end_date)
