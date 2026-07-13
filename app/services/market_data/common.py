"""Shared market-data types and helpers used by all providers."""

from __future__ import annotations

from typing import Any

import pandas as pd

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


def clip_ohlcv_to_end_date(df: pd.DataFrame, end_date: str) -> pd.DataFrame:
    """Include all bars on end_date, including intraday timestamps after midnight."""
    end_exclusive = pd.Timestamp(end_date) + pd.Timedelta(days=1)
    return df[df.index < end_exclusive]


def normalize_vn_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol:
        return ""
    if symbol.endswith(".VN") or symbol.startswith("^"):
        return symbol
    return f"{symbol}.VN"


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
