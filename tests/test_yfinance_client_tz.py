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
    """Sparse ranged history triggers period fallback; Bangkok tz must strip before compare."""
    ranged = _tz_aware_ohlcv(n=50)  # < 500 → fallback
    full = _tz_aware_ohlcv(n=200)

    stock = MagicMock()
    stock.history.side_effect = [ranged, pd.DataFrame(), full]

    with patch("app.services.market_data.yfinance_client.yf.Ticker", return_value=stock):
        df = YFinanceClient().get_ohlcv("FUEVFVND.VN", "2025-05-01", "2026-05-01")

    assert not df.empty
    assert getattr(df.index, "tz", None) is None
    assert df.index.max() <= pd.Timestamp("2026-05-01")


def test_get_ohlcv_vnindex_uses_five_day_period_only() -> None:
    """VN-Index on Yahoo only supports 5d OHLCV; skip ranged and max fallbacks."""
    short = _tz_aware_ohlcv(n=5)

    stock = MagicMock()
    stock.history.return_value = short

    with patch("app.services.market_data.yfinance_client.yf.Ticker", return_value=stock):
        df = YFinanceClient().get_ohlcv("^VNINDEX.VN", "2025-01-01", "2026-01-01")

    stock.history.assert_called_once_with(period="5d", interval="4h")
    assert not df.empty
    assert len(df) == 5


def test_clip_ohlcv_to_end_date_includes_intraday_bars_on_last_day() -> None:
    idx = pd.to_datetime(
        [
            "2026-07-09 09:00:00",
            "2026-07-09 13:00:00",
            "2026-07-10 09:00:00",
            "2026-07-10 13:00:00",
        ]
    )
    df = pd.DataFrame(
        {"Open": [1, 2, 3, 4], "High": [1, 2, 3, 4], "Low": [1, 2, 3, 4], "Close": [1, 2, 3, 4]},
        index=idx,
    )

    from app.services.market_data.common import clip_ohlcv_to_end_date

    clipped = clip_ohlcv_to_end_date(df, "2026-07-10")
    assert len(clipped) == 4
    assert clipped.index[-1] == pd.Timestamp("2026-07-10 13:00:00")


def test_get_ohlcv_raises_when_empty() -> None:
    stock = MagicMock()
    stock.history.return_value = pd.DataFrame()

    with patch("app.services.market_data.yfinance_client.yf.Ticker", return_value=stock):
        with pytest.raises(Exception, match="No data found"):
            YFinanceClient().get_ohlcv("BAD.VN", "2025-01-01", "2025-06-01")
