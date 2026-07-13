"""Market data provider factory selection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.services.market_data.factory import get_market_data_client, get_market_data_provider
from app.services.market_data.vnstock_provider import VnstockProvider
from app.services.market_data.yfinance_provider import YFinanceProvider


def test_get_market_data_provider_yfinance() -> None:
    settings = Settings(market_data_provider="yfinance")
    assert isinstance(get_market_data_provider(settings), YFinanceProvider)


def test_get_market_data_provider_vnstock() -> None:
    settings = Settings(market_data_provider="vnstock")
    with patch("app.services.market_data.vnstock_provider.VnstockClient") as mock_client:
        provider = get_market_data_provider(settings)
    assert isinstance(provider, VnstockProvider)
    mock_client.assert_called_once_with()


def test_get_market_data_client_vnstock() -> None:
    settings = Settings(market_data_provider="vnstock")
    with patch("app.services.market_data.factory.VnstockClient") as mock_client:
        mock_client.return_value = MagicMock()
        client = get_market_data_client(settings)
    mock_client.assert_called_once_with()
    assert client is mock_client.return_value
