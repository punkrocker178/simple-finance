from __future__ import annotations

import pandas as pd

from app.services.market_data.vnstock_client import VnstockClient


class VnstockProvider:
    def __init__(self, client: VnstockClient | None = None, api_key: str | None = None) -> None:
        self._client = client or VnstockClient(api_key=api_key)

    def get_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        *,
        length: str | int | None = None,
    ) -> pd.DataFrame:
        return self._client.get_ohlcv(ticker, start_date, end_date, length=length)
