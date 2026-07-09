"""Regression: tz-aware yfinance indexes must not break end_date filtering."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services.market_data.yfinance_client import YFinanceClient


def _tz_aware_ohlcv(n: int = 100, tz: str = "Asia/Bangkok") -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="B", tz=tz)
    return pd.DataFrame(
        {
            "Open": range(n),
            "High": range(1, n + 1),
            "Low": range(n),
            "Close": range(n),
            "Volume": [1000] * n,
        },
        index=idx,
    )


def test_get_ohlcv_fallback_clips_tz_aware_index_without_raising() -> None:
    """Sparse ranged history triggers max-period fallback; Bangkok tz must strip before compare."""
    ranged = _tz_aware_ohlcv(n=50)  # < 500 → fallback
    full = _tz_aware_ohlcv(n=200)

    stock = MagicMock()
    stock.history.side_effect = [ranged, full]

    with patch("app.services.market_data.yfinance_client.yf.Ticker", return_value=stock):
        df = YFinanceClient().get_ohlcv("FUEVFVND.VN", "2025-05-01", "2026-05-01")

    assert not df.empty
    assert getattr(df.index, "tz", None) is None
    assert df.index.max() <= pd.Timestamp("2026-05-01")


def test_get_ohlcv_raises_when_empty() -> None:
    stock = MagicMock()
    stock.history.return_value = pd.DataFrame()

    with patch("app.services.market_data.yfinance_client.yf.Ticker", return_value=stock):
        with pytest.raises(Exception, match="No data found"):
            YFinanceClient().get_ohlcv("BAD.VN", "2025-01-01", "2025-06-01")
