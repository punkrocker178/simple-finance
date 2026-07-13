"""Thin facade over vnstock for OHLCV, ticker info, and market summaries."""

from __future__ import annotations

import re
from typing import Any, Literal

import pandas as pd

from app.core.config import Settings, get_settings

from app.services.market_data.common import (
    TICKER_INFO_KEYS,
    MarketDataError,
    clip_ohlcv_to_end_date,
    normalize_vn_symbol,
    ohlcv_to_records as _ohlcv_to_records,
    safe_float,
)

TickerKind = Literal["equity", "index", "etf"]

VN_INDEX_SYMBOLS = frozenset(
    {"VNINDEX", "HNXINDEX", "UPCOMINDEX", "VN30", "HNX30", "VN100"}
)
VN_ETF_PREFIXES = ("E1", "FUE", "FUETF")

_LENGTH_PERIOD_DAYS: dict[str, int] = {
    "1W": 7,
    "2W": 14,
    "3W": 21,
    "6W": 45,
    "1M": 30,
    "2M": 60,
    "3M": 90,
    "4M": 120,
    "5M": 150,
    "6M": 180,
    "9M": 270,
    "1Y": 365,
    "18M": 540,
    "2Y": 730,
    "3Y": 1095,
    "5Y": 1825,
    "1Q": 90,
}

_MAX_OHLCV_COUNT = 10_000


def _to_vnstock_symbol(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if symbol.startswith("^"):
        symbol = symbol[1:]
    if symbol.endswith(".VN"):
        symbol = symbol[:-3]
    return symbol


def _classify_ticker(ticker: str) -> tuple[str, TickerKind]:
    raw = ticker.strip().upper()
    symbol = _to_vnstock_symbol(ticker)
    if raw.startswith("^") or symbol in VN_INDEX_SYMBOLS:
        return symbol, "index"
    if symbol.startswith(VN_ETF_PREFIXES):
        return symbol, "etf"
    return symbol, "equity"


_configured_api_key: str | None = None


def init_vnstock(settings: Settings | None = None) -> None:
    """Register vnstock API key once at application startup."""
    settings = settings or get_settings()
    if settings.market_data_provider.lower().strip() != "vnstock":
        return

    api_key = settings.vnstock_api_key.strip()
    if not api_key:
        return

    global _configured_api_key
    if _configured_api_key == api_key:
        return
    _configured_api_key = api_key

    try:
        from vnai import setup_api_key

        setup_api_key(api_key)
        return
    except ImportError:
        pass

    from vnstock import register_user

    register_user(api_key=api_key)


def _normalize_vnstock_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    colmap = {c: c.lower() for c in out.columns}
    out = out.rename(columns=colmap)

    if "time" in out.columns:
        out["time"] = pd.to_datetime(out["time"])
        out = out.set_index("time")
    elif out.index.name and str(out.index.name).lower() in {"time", "date"}:
        out.index = pd.to_datetime(out.index)
    elif not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index)

    rename = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
    }
    missing = [src for src in rename if src not in out.columns]
    if missing:
        raise MarketDataError(f"OHLCV response missing columns: {missing}")

    out = out.rename(columns=rename)
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_localize(None)
    return out.sort_index()[["Open", "High", "Low", "Close"]]


def _length_to_count(length: str | int) -> int:
    if isinstance(length, int):
        if length <= 0:
            raise MarketDataError("length must be a positive integer.")
        return min(length, _MAX_OHLCV_COUNT)

    token = length.strip().upper()
    if not token:
        raise MarketDataError("length must not be empty.")

    bars_match = re.fullmatch(r"(\d+)B", token)
    if bars_match:
        return min(int(bars_match.group(1)), _MAX_OHLCV_COUNT)

    days_match = re.fullmatch(r"(\d+)D", token)
    if days_match:
        return min(int(days_match.group(1)), _MAX_OHLCV_COUNT)

    if token in _LENGTH_PERIOD_DAYS:
        return _LENGTH_PERIOD_DAYS[token]

    if token.isdigit():
        return min(int(token), _MAX_OHLCV_COUNT)

    raise MarketDataError(f"Unsupported length format: {length!r}")


def _ohlcv_count(start_date: str, end_date: str, length: str | int | None) -> int:
    if length is not None:
        return _length_to_count(length)
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if end < start:
        raise MarketDataError("end_date must be on or after start_date.")
    return min((end - start).days + 1, _MAX_OHLCV_COUNT)


def _first_row_value(row: pd.Series, *keys: str) -> Any:
    for key in keys:
        if key in row and pd.notna(row[key]):
            return row[key]
    return None


class VnstockClient:
    def __init__(self) -> None:
        from vnstock import Market, Reference

        self._market = Market()
        self._reference = Reference()

    def get_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        *,
        length: str | int | None = None,
    ) -> pd.DataFrame:
        symbol, kind = _classify_ticker(ticker)
        count = _ohlcv_count(start_date, end_date, length)
        ohlcv_kwargs = {
            "start": start_date,
            "end": end_date,
            "resolution": "1D",
            "count": count,
        }
        try:
            if kind == "index":
                raw = self._market.index(symbol=symbol).ohlcv(**ohlcv_kwargs)
            elif kind == "etf":
                raw = self._market.etf(symbol=symbol).ohlcv(**ohlcv_kwargs)
            else:
                raw = self._market.equity(symbol=symbol).ohlcv(**ohlcv_kwargs)
        except Exception as exc:
            raise MarketDataError(f"Failed to fetch OHLCV for {ticker}: {exc}") from exc

        df = _normalize_vnstock_ohlcv(raw)
        if df.empty:
            raise MarketDataError(f"No data found for {ticker}.")

        df = clip_ohlcv_to_end_date(df, end_date)
        if df.empty:
            raise MarketDataError(f"No data found for {ticker}.")
        return df

    def get_ticker_info(self, ticker: str) -> dict[str, Any]:
        symbol, kind = _classify_ticker(ticker)
        try:
            profile_info: dict[str, Any] | None = None
            outstanding_shares: float | None = None
            if kind == "equity":
                profile = self._reference.company(symbol=symbol).info()
                if profile is not None and not profile.empty:
                    profile_row = profile.iloc[0]
                    profile_info = self._map_company_profile(ticker, profile_row)
                    outstanding_shares = safe_float(
                        _first_row_value(
                            profile_row,
                            "outstanding_shares",
                            "issued_share",
                            "issue_share",
                        )
                    )

            quote_info: dict[str, Any] | None = None
            quote = self._fetch_quote(symbol, kind)
            if quote is not None and not quote.empty:
                quote_info = self._map_quote_info(ticker, quote.iloc[0], kind)

            if profile_info and quote_info:
                return self._merge_equity_info(
                    profile_info, quote_info, outstanding_shares=outstanding_shares
                )
            if quote_info:
                return quote_info
            if profile_info:
                return profile_info
        except MarketDataError:
            raise
        except Exception as exc:
            raise MarketDataError(f"Failed to fetch info for {ticker}: {exc}") from exc

        raise MarketDataError(f"Ticker not found: {ticker}")

    def get_fast_info(self, ticker: str) -> dict[str, Any]:
        symbol, kind = _classify_ticker(ticker)
        try:
            quote = self._fetch_quote(symbol, kind)
        except Exception as exc:
            raise MarketDataError(f"Failed to fetch fast info for {ticker}: {exc}") from exc

        if quote is None or quote.empty:
            raise MarketDataError(f"No fast info for {ticker}.")

        row = quote.iloc[0]
        return {
            "symbol": ticker,
            "last_price": safe_float(
                _first_row_value(row, "close_price", "match_price", "close", "price")
            ),
            "previous_close": safe_float(
                _first_row_value(row, "reference_price", "previous_close", "prev_close")
            ),
            "open": safe_float(_first_row_value(row, "open_price", "open")),
            "day_high": safe_float(_first_row_value(row, "high_price", "high", "day_high")),
            "day_low": safe_float(_first_row_value(row, "low_price", "low", "day_low")),
            "year_high": safe_float(_first_row_value(row, "year_high", "fifty_two_week_high")),
            "year_low": safe_float(_first_row_value(row, "year_low", "fifty_two_week_low")),
            "currency": _first_row_value(row, "currency") or "VND",
            "exchange": _first_row_value(row, "exchange", "exchange_name", "exchange_code_mic"),
            "market_cap": safe_float(_first_row_value(row, "market_cap", "marketCap")),
        }

    def search_vn_tickers(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        try:
            results_df = self._reference.search.symbol(
                query=query, locale="vi-vn", limit=limit * 3
            )
        except Exception as exc:
            raise MarketDataError(f"Ticker search failed: {exc}") from exc

        if results_df is None or results_df.empty:
            return []

        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for _, row in results_df.iterrows():
            raw_symbol = str(_first_row_value(row, "symbol", "RT00S") or "").strip().upper()
            if not raw_symbol:
                continue
            symbol = normalize_vn_symbol(raw_symbol)
            if symbol in seen:
                continue
            seen.add(symbol)
            results.append(
                {
                    "symbol": symbol,
                    "short_name": _first_row_value(
                        row, "short_name", "friendly_name", "local_name", "AC042"
                    ),
                    "long_name": _first_row_value(
                        row, "eng_name", "description", "friendly_name", "RT0SN"
                    ),
                    "exchange": _first_row_value(row, "exchange_name", "exchange_code_mic", "AC040"),
                    "quote_type": _first_row_value(row, "quote_type"),
                }
            )
            if len(results) >= limit:
                break
        return results

    def get_market_summary(self, symbols: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for symbol in symbols:
            try:
                results.append(self.get_fast_info(symbol))
            except MarketDataError as exc:
                results.append({"symbol": symbol, "error": str(exc)})
        return results

    @staticmethod
    def ohlcv_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
        return _ohlcv_to_records(df)

    def _fetch_quote(self, symbol: str, kind: TickerKind) -> pd.DataFrame | None:
        if kind == "index":
            return self._market.index(symbol=symbol).quote()
        if kind == "etf":
            return self._market.etf(symbol=symbol).quote()
        return self._market.equity(symbol=symbol).quote()

    def _map_company_profile(self, ticker: str, row: pd.Series) -> dict[str, Any]:
        short_name = _first_row_value(
            row, "short_name", "name", "company_name", "organ_short_name", "symbol"
        )
        long_name = _first_row_value(
            row,
            "name",
            "company_name",
            "eng_name",
            "organ_name",
            "long_name",
            "short_name",
            "symbol",
        )
        info = {key: None for key in TICKER_INFO_KEYS}
        info.update(
            {
                "symbol": ticker,
                "shortName": short_name,
                "longName": long_name,
                "exchange": _first_row_value(row, "exchange"),
                "quoteType": "EQUITY",
                "currency": "VND",
                "market": "vn",
                "sector": _first_row_value(
                    row, "sector", "vi_sector", "icb_name2", "icb_name3"
                ),
                "industry": _first_row_value(
                    row, "industry", "industry_en", "icb_name3", "icb_name4"
                ),
                "marketCap": safe_float(_first_row_value(row, "market_cap", "marketCap")),
            }
        )
        return info

    def _map_quote_info(self, ticker: str, row: pd.Series, kind: TickerKind) -> dict[str, Any]:
        quote_type = {"equity": "EQUITY", "index": "INDEX", "etf": "ETF"}[kind]
        info = {key: None for key in TICKER_INFO_KEYS}
        info.update(
            {
                "symbol": ticker,
                "shortName": _first_row_value(row, "short_name", "symbol"),
                "longName": _first_row_value(row, "short_name", "symbol"),
                "exchange": _first_row_value(row, "exchange", "exchange_name"),
                "quoteType": quote_type,
                "currency": "VND",
                "market": "vn",
                "marketCap": safe_float(_first_row_value(row, "market_cap", "marketCap")),
                "previousClose": safe_float(
                    _first_row_value(row, "reference_price", "previous_close")
                ),
                "regularMarketPrice": safe_float(
                    _first_row_value(row, "close_price", "match_price", "close")
                ),
                "fiftyTwoWeekHigh": safe_float(
                    _first_row_value(row, "year_high", "fifty_two_week_high", "high_price")
                ),
                "fiftyTwoWeekLow": safe_float(
                    _first_row_value(row, "year_low", "fifty_two_week_low", "low_price")
                ),
                "trailingPE": safe_float(_first_row_value(row, "pe", "trailing_pe")),
                "dividendYield": safe_float(
                    _first_row_value(row, "dividend_yield", "dividendYield")
                ),
                "volume": safe_float(
                    _first_row_value(row, "volume_accumulated", "volume_last", "volume")
                ),
                "averageVolume": safe_float(
                    _first_row_value(row, "average_volume", "avg_volume", "averageVolume")
                ),
            }
        )
        return info

    @staticmethod
    def _merge_equity_info(
        profile_info: dict[str, Any],
        quote_info: dict[str, Any],
        *,
        outstanding_shares: float | None = None,
    ) -> dict[str, Any]:
        """Company profile for identity; quote for live market fields."""
        merged = {key: None for key in TICKER_INFO_KEYS}
        quote_price_keys = {
            "previousClose",
            "regularMarketPrice",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
            "volume",
            "averageVolume",
            "trailingPE",
            "dividendYield",
        }
        for key, value in profile_info.items():
            if key in TICKER_INFO_KEYS and value is not None:
                merged[key] = value
        for key, value in quote_info.items():
            if value is None:
                continue
            if key in quote_price_keys or merged.get(key) is None:
                merged[key] = value
        if (
            merged.get("marketCap") is None
            and outstanding_shares
            and merged.get("regularMarketPrice")
        ):
            merged["marketCap"] = outstanding_shares * merged["regularMarketPrice"]
        return merged
