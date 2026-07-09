from __future__ import annotations

import pandas as pd

from app.services.market_data.yfinance_client import YFinanceClient


class YFinanceProvider:
    def __init__(self, client: YFinanceClient | None = None) -> None:
        self._client = client or YFinanceClient()

    def get_ohlcv(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._client.get_ohlcv(ticker, start_date, end_date)
