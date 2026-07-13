"""Vnstock client symbol helpers and OHLCV normalization."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.services.market_data.vnstock_client import (
    VnstockClient,
    _classify_ticker,
    _length_to_count,
    _normalize_vnstock_ohlcv,
    _ohlcv_count,
    _to_vnstock_symbol,
)


def test_to_vnstock_symbol_strips_yahoo_suffix_and_caret() -> None:
    assert _to_vnstock_symbol("VNM.VN") == "VNM"
    assert _to_vnstock_symbol("^VNINDEX.VN") == "VNINDEX"
    assert _to_vnstock_symbol("E1VFVN30.VN") == "E1VFVN30"


def test_classify_ticker_detects_index_and_etf() -> None:
    assert _classify_ticker("^VNINDEX.VN") == ("VNINDEX", "index")
    assert _classify_ticker("FUEVFVND.VN") == ("FUEVFVND", "etf")
    assert _classify_ticker("VNM.VN") == ("VNM", "equity")


def test_normalize_vnstock_ohlcv_maps_lowercase_columns() -> None:
    raw = pd.DataFrame(
        {
            "time": ["2024-01-02", "2024-01-03"],
            "open": [10.0, 11.0],
            "high": [12.0, 13.0],
            "low": [9.0, 10.0],
            "close": [11.0, 12.0],
            "volume": [100, 200],
        }
    )
    df = _normalize_vnstock_ohlcv(raw)
    assert list(df.columns) == ["Open", "High", "Low", "Close"]
    assert len(df) == 2
    assert getattr(df.index, "tz", None) is None


def _make_client(*, market: MagicMock, reference: MagicMock) -> VnstockClient:
    client = VnstockClient.__new__(VnstockClient)
    client._market = market
    client._reference = reference
    return client


def test_length_to_count_parses_bars_and_periods() -> None:
    assert _length_to_count(250) == 250
    assert _length_to_count("100b") == 100
    assert _length_to_count("1Y") == 365
    assert _length_to_count("10D") == 10


def test_ohlcv_count_defaults_to_calendar_span() -> None:
    assert _ohlcv_count("2024-01-01", "2024-12-31", None) == 366


def test_get_ohlcv_equity_uses_market_equity_and_clips_end_date() -> None:
    raw = pd.DataFrame(
        {
            "time": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "open": [1, 2, 3],
            "high": [2, 3, 4],
            "low": [1, 2, 3],
            "close": [2, 3, 4],
            "volume": [10, 20, 30],
        }
    )
    equity = MagicMock()
    equity.ohlcv.return_value = raw
    market = MagicMock()
    market.equity.return_value = equity

    client = _make_client(market=market, reference=MagicMock())
    df = client.get_ohlcv("VNM.VN", "2024-01-01", "2024-01-02")

    market.equity.assert_called_once_with(symbol="VNM")
    equity.ohlcv.assert_called_once_with(
        start="2024-01-01",
        end="2024-01-02",
        resolution="1D",
        count=2,
    )
    assert len(df) == 2
    assert df.index.max() <= pd.Timestamp("2024-01-02")


def test_get_ohlcv_passes_explicit_length_as_count() -> None:
    raw = pd.DataFrame(
        {
            "time": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "open": [1, 2],
            "high": [2, 3],
            "low": [1, 2],
            "close": [2, 3],
            "volume": [10, 20],
        }
    )
    equity = MagicMock()
    equity.ohlcv.return_value = raw
    market = MagicMock()
    market.equity.return_value = equity

    client = _make_client(market=market, reference=MagicMock())
    client.get_ohlcv("VNM.VN", "2024-01-01", "2024-12-31", length="500b")

    equity.ohlcv.assert_called_once_with(
        start="2024-01-01",
        end="2024-12-31",
        resolution="1D",
        count=500,
    )


def test_get_ohlcv_raises_when_empty() -> None:
    equity = MagicMock()
    equity.ohlcv.return_value = pd.DataFrame()
    market = MagicMock()
    market.equity.return_value = equity

    client = _make_client(market=market, reference=MagicMock())
    with pytest.raises(Exception, match="No data found"):
        client.get_ohlcv("BAD.VN", "2024-01-01", "2024-01-31")


def test_get_ticker_info_equity_merges_profile_and_quote() -> None:
    profile = pd.DataFrame(
        [
            {
                "symbol": "HPG",
                "name": "Hoa Phat Group",
                "short_name": "Hoa Phat",
                "exchange": "HOSE",
                "sector": "Materials",
                "industry": "Steel",
                "business_model": "Steel production...",
                "listed_volume": 8443,
                "outstanding_shares": 8_000_000_000,
            }
        ]
    )
    quote = pd.DataFrame(
        [
            {
                "symbol": "HPG",
                "exchange": "HOSE",
                "reference_price": 22950,
                "close_price": 22450,
                "high_price": 22950,
                "low_price": 22400,
                "volume_accumulated": 23_572_700,
                "year_high": 30000,
                "year_low": 18000,
            }
        ]
    )
    company = MagicMock()
    company.info.return_value = profile
    reference = MagicMock()
    reference.company.return_value = company
    equity = MagicMock()
    equity.quote.return_value = quote
    market = MagicMock()
    market.equity.return_value = equity

    client = _make_client(market=market, reference=reference)
    info = client.get_ticker_info("HPG.VN")

    assert info["symbol"] == "HPG.VN"
    assert info["shortName"] == "Hoa Phat"
    assert info["longName"] == "Hoa Phat Group"
    assert info["exchange"] == "HOSE"
    assert info["quoteType"] == "EQUITY"
    assert info["sector"] == "Materials"
    assert info["industry"] == "Steel"
    assert info["previousClose"] == 22950.0
    assert info["regularMarketPrice"] == 22450.0
    assert info["fiftyTwoWeekHigh"] == 30000.0
    assert info["fiftyTwoWeekLow"] == 18000.0
    assert info["volume"] == 23_572_700.0
    assert info["volume"] != 8443


def test_search_vn_tickers_normalizes_symbols() -> None:
    search_df = pd.DataFrame(
        [
            {
                "symbol": "VNM",
                "short_name": "Vinamilk",
                "eng_name": "Vietnam Dairy Products JSC",
                "exchange_name": "HOSE",
            }
        ]
    )
    search = MagicMock()
    search.symbol.return_value = search_df
    reference = MagicMock()
    reference.search = search

    client = _make_client(market=MagicMock(), reference=reference)
    results = client.search_vn_tickers("vinamilk", limit=5)

    assert results[0]["symbol"] == "VNM.VN"
    assert results[0]["short_name"] == "Vinamilk"
