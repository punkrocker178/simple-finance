"""Thin facade over yfinance for OHLCV, ticker info, and market summaries."""

from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf

TICKER_INFO_KEYS = (
    "symbol",
    "shortName",
    "longName",
    "exchange",
    "quoteType",
    "currency",
    "market",
    "sector",
    "industry",
    "marketCap",
    "previousClose",
    "regularMarketPrice",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "trailingPE",
    "dividendYield",
    "volume",
    "averageVolume",
)


class MarketDataError(Exception):
    """Raised when market data cannot be retrieved or normalized."""


OHLCV_PERIOD_FALLBACKS = ("max", "1y", "1mo", "5d")
OHLCV_FIVE_DAY_ONLY_TICKERS = frozenset({"^VNINDEX.VN"})
VN_EXCHANGES = frozenset({"VSE", "HOSE", "HNX", "UPCOM"})


def _clip_ohlcv_to_end_date(df: pd.DataFrame, end_date: str) -> pd.DataFrame:
    """Include all bars on end_date, including intraday timestamps after midnight."""
    end_exclusive = pd.Timestamp(end_date) + pd.Timedelta(days=1)
    return df[df.index < end_exclusive]


class YFinanceClient:
    def get_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        *,
        length: str | int | None = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV. On sparse/empty ranged history, tries shorter period fallbacks."""
        stock = yf.Ticker(ticker)

        if ticker in OHLCV_FIVE_DAY_ONLY_TICKERS:
            df = stock.history(period="5d", interval="4h")
        else:
            df = stock.history(start=start_date, end=end_date)

            if df.empty or len(df) < 500:
                for period in OHLCV_PERIOD_FALLBACKS:
                    candidate = stock.history(period=period)
                    if not candidate.empty:
                        df = candidate
                        break

        if not df.empty:
            df = self._normalize_ohlcv_index(df)
            df = _clip_ohlcv_to_end_date(df, end_date)

        if df.empty:
            raise MarketDataError(f"No data found for {ticker}.")

        df = self._normalize_ohlcv_index(df[["Open", "High", "Low", "Close"]].copy())
        return df

    @staticmethod
    def _normalize_ohlcv_index(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if getattr(out.index, "tz", None) is not None:
            out.index = out.index.tz_localize(None)
        return out

    def get_ticker_info(self, ticker: str) -> dict[str, Any]:
        stock = yf.Ticker(ticker)
        try:
            raw = stock.info or {}
        except Exception as exc:  # yfinance can raise on bad symbols / network
            raise MarketDataError(f"Failed to fetch info for {ticker}: {exc}") from exc

        if not raw or (raw.get("quoteType") is None and raw.get("regularMarketPrice") is None and not raw.get("shortName")):
            # Some symbols still return a sparse dict; try fast_info as a signal of existence
            try:
                fast = dict(stock.fast_info)
            except Exception:
                fast = {}
            if not fast and not raw:
                raise MarketDataError(f"Ticker not found: {ticker}")

        info = {key: raw.get(key) for key in TICKER_INFO_KEYS}
        info["symbol"] = info.get("symbol") or ticker
        return info

    def get_fast_info(self, ticker: str) -> dict[str, Any]:
        stock = yf.Ticker(ticker)
        try:
            fast = dict(stock.fast_info)
        except Exception as exc:
            raise MarketDataError(f"Failed to fetch fast info for {ticker}: {exc}") from exc

        if not fast:
            raise MarketDataError(f"No fast info for {ticker}.")

        return {
            "symbol": ticker,
            "last_price": _safe_float(fast.get("last_price") or fast.get("lastPrice")),
            "previous_close": _safe_float(fast.get("previous_close") or fast.get("previousClose")),
            "open": _safe_float(fast.get("open")),
            "day_high": _safe_float(fast.get("day_high") or fast.get("dayHigh")),
            "day_low": _safe_float(fast.get("day_low") or fast.get("dayLow")),
            "year_high": _safe_float(fast.get("year_high") or fast.get("yearHigh")),
            "year_low": _safe_float(fast.get("year_low") or fast.get("yearLow")),
            "currency": fast.get("currency"),
            "exchange": fast.get("exchange"),
            "market_cap": _safe_float(fast.get("market_cap") or fast.get("marketCap")),
        }

    def search_vn_tickers(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search Yahoo Finance and return Vietnamese-market tickers only."""
        search = yf.Search(query, max_results=limit * 3)
        seen: set[str] = set()
        results: list[dict[str, Any]] = []

        for quote in search.quotes:
            if not _is_vietnam_quote(quote):
                continue
            symbol = _normalize_vn_symbol(quote.get("symbol", ""))
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            results.append(
                {
                    "symbol": symbol,
                    "short_name": quote.get("shortname") or quote.get("shortName"),
                    "long_name": quote.get("longname") or quote.get("longName"),
                    "exchange": quote.get("exchange"),
                    "quote_type": quote.get("quoteType"),
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
        records: list[dict[str, Any]] = []
        for idx, row in df.iterrows():
            records.append(
                {
                    "date": pd.Timestamp(idx).strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                }
            )
        return records


def _is_vietnam_quote(quote: dict[str, Any]) -> bool:
    symbol = str(quote.get("symbol", ""))
    if symbol.endswith(".VN"):
        return True
    exchange = str(quote.get("exchange", "")).upper()
    return exchange in VN_EXCHANGES


def _normalize_vn_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol:
        return ""
    if symbol.endswith(".VN") or symbol.startswith("^"):
        return symbol
    return f"{symbol}.VN"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
