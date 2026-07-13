"""Vietnamese ticker search filtering and normalization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.market_data.common import normalize_vn_symbol
from app.services.market_data.yfinance_client import (
    YFinanceClient,
    _is_vietnam_quote,
)


def test_normalize_vn_symbol_appends_suffix() -> None:
    assert normalize_vn_symbol("vnm") == "VNM.VN"
    assert normalize_vn_symbol("E1VFVN30.VN") == "E1VFVN30.VN"
    assert normalize_vn_symbol("^VNINDEX.VN") == "^VNINDEX.VN"


def test_is_vietnam_quote_by_suffix_or_exchange() -> None:
    assert _is_vietnam_quote({"symbol": "VNM.VN"})
    assert _is_vietnam_quote({"symbol": "VNM", "exchange": "HOSE"})
    assert not _is_vietnam_quote({"symbol": "AAPL", "exchange": "NMS"})


def test_search_vn_tickers_filters_and_normalizes() -> None:
    mock_search = MagicMock()
    mock_search.quotes = [
        {"symbol": "VNM.VN", "shortname": "Vinamilk", "exchange": "HOSE", "quoteType": "EQUITY"},
        {"symbol": "AAPL", "shortname": "Apple", "exchange": "NMS", "quoteType": "EQUITY"},
        {"symbol": "FPT", "shortname": "FPT Corp", "exchange": "HOSE", "quoteType": "EQUITY"},
        {"symbol": "VNM.VN", "shortname": "Dup", "exchange": "HOSE", "quoteType": "EQUITY"},
    ]

    with patch("app.services.market_data.yfinance_client.yf.Search", return_value=mock_search):
        results = YFinanceClient().search_vn_tickers("vn", limit=10)

    symbols = [r["symbol"] for r in results]
    assert symbols == ["VNM.VN", "FPT.VN"]
    assert results[0]["short_name"] == "Vinamilk"
    assert results[1]["short_name"] == "FPT Corp"


def test_search_tickers_api_route() -> None:
    mock_search = MagicMock()
    mock_search.quotes = [
        {"symbol": "E1VFVN30.VN", "shortname": "VFMVN30 ETF", "exchange": "HOSE", "quoteType": "ETF"},
    ]

    with patch("app.services.market_data.yfinance_client.yf.Search", return_value=mock_search):
        client = TestClient(app)
        resp = client.get("/api/v1/market/tickers/search", params={"q": "vfvn"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["symbol"] == "E1VFVN30.VN"
