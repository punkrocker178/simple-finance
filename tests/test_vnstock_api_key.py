"""vnstock API key is configured once at application startup."""

from __future__ import annotations

from unittest.mock import patch

import app.services.market_data.vnstock_client as vnstock_client_module
from app.core.config import Settings
from app.services.market_data.vnstock_client import init_vnstock


def setup_function() -> None:
    vnstock_client_module._configured_api_key = None


def test_init_vnstock_skips_when_provider_is_not_vnstock() -> None:
    with patch("vnai.setup_api_key") as mock_setup:
        init_vnstock(Settings(market_data_provider="yfinance", vnstock_api_key="vnstock_test"))
    mock_setup.assert_not_called()


def test_init_vnstock_skips_when_api_key_missing() -> None:
    with patch("vnai.setup_api_key") as mock_setup:
        init_vnstock(Settings(market_data_provider="vnstock", vnstock_api_key=""))
    mock_setup.assert_not_called()


def test_init_vnstock_calls_setup_api_key_once() -> None:
    with patch("vnai.setup_api_key") as mock_setup:
        init_vnstock(Settings(market_data_provider="vnstock", vnstock_api_key="vnstock_test_key"))
        init_vnstock(Settings(market_data_provider="vnstock", vnstock_api_key="vnstock_test_key"))
    mock_setup.assert_called_once_with("vnstock_test_key")
