from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.api.schemas.market import (
    MarketSummaryResponse,
    OhlcvResponse,
    TickerInfoResponse,
    TickerSearchResponse,
)
from app.core.config import get_settings
from app.services.market_data.factory import get_market_data_client
from app.services.market_data.yfinance_client import MarketDataError

router = APIRouter()


def _client():
    return get_market_data_client()


@router.get("/tickers/search", response_model=TickerSearchResponse)
def search_tickers(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
) -> TickerSearchResponse:
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query must not be empty")
    try:
        items = _client().search_vn_tickers(query, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream market data error: {exc}") from exc
    return TickerSearchResponse(items=items)


@router.get("/tickers/{ticker}", response_model=TickerInfoResponse)
def get_ticker(ticker: str) -> dict:
    try:
        return _client().get_ticker_info(ticker)
    except MarketDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream market data error: {exc}") from exc


@router.get("/tickers/{ticker}/ohlcv", response_model=OhlcvResponse)
def get_ticker_ohlcv(
    ticker: str,
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    length: str | int | None = Query(
        None,
        description=(
            "Max bars to fetch (e.g. 500, '1Y', '100b'). "
            "Defaults to the calendar span between start and end."
        ),
    ),
) -> OhlcvResponse:
    try:
        df = _client().get_ohlcv(ticker, start, end, length=length)
        # Client may include pre-start warmup rows on max-period fallback; clip for API.
        df = df[df.index >= pd.Timestamp(start)]
        if df.empty:
            raise MarketDataError(
                f"No OHLCV bars for {ticker} between {start} and {end}."
            )
    except MarketDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream market data error: {exc}") from exc

    return OhlcvResponse(
        ticker=ticker,
        start=start,
        end=end,
        bars=_client().ohlcv_to_records(df),
    )


@router.get("/summary", response_model=MarketSummaryResponse)
def get_market_summary(
    symbols: str | None = Query(
        None,
        description="Comma-separated tickers; defaults to MARKET_SUMMARY_SYMBOLS",
    ),
) -> MarketSummaryResponse:
    settings = get_settings()
    if symbols:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    else:
        symbol_list = settings.market_summary_symbol_list

    try:
        items = _client().get_market_summary(symbol_list)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream market data error: {exc}") from exc

    return MarketSummaryResponse(symbols=symbol_list, items=items)
