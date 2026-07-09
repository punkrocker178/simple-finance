from __future__ import annotations

from typing import Protocol

import pandas as pd


class MarketDataProvider(Protocol):
    def get_ohlcv(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Return OHLCV with Open/High/Low/Close columns and a tz-naive DatetimeIndex."""
        ...
