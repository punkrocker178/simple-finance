"""HTTP OHLCV provider for a configurable REST market-data API.

Expected JSON response (list or object with `data` list):
[
  {"date": "2024-01-01", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5},
  ...
]
"""

from __future__ import annotations

from typing import Any

import httpx
import pandas as pd

from app.core.config import Settings
from app.services.market_data.common import MarketDataError


class HttpProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_ohlcv(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        path = self._settings.market_data_ohlcv_path.format(ticker=ticker)
        url = self._settings.market_data_base_url.rstrip("/") + "/" + path.lstrip("/")
        params = {
            self._settings.market_data_start_param: start_date,
            self._settings.market_data_end_param: end_date,
        }
        headers: dict[str, str] = {}
        if self._settings.market_data_api_key:
            headers["Authorization"] = f"Bearer {self._settings.market_data_api_key}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise MarketDataError(f"HTTP market data request failed: {exc}") from exc

        rows = _extract_rows(payload)
        if not rows:
            raise MarketDataError(f"No OHLCV rows returned for {ticker}.")

        frame = pd.DataFrame(rows)
        required = {"date", "open", "high", "low", "close"}
        colmap = {c: c.lower() for c in frame.columns}
        frame = frame.rename(columns=colmap)
        missing = required - set(frame.columns)
        if missing:
            raise MarketDataError(f"HTTP OHLCV response missing columns: {sorted(missing)}")

        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date").sort_index()
        frame = frame.rename(
            columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}
        )
        return frame[["Open", "High", "Low", "Close"]].astype(float)


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "results", "ohlcv", "bars"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []
