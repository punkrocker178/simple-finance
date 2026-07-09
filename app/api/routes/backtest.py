from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas.backtest import (
    BacktestReport,
    BacktestRequest,
    BacktestRunListResponse,
    BacktestRunSummary,
)
from app.core.db import get_db
from app.services.backtest_service import (
    BacktestServiceError,
    get_backtest_run,
    list_backtest_runs,
    run_and_persist_dca_backtest,
)

router = APIRouter()


def _to_report(row) -> BacktestReport:
    result = row.result or {}
    return BacktestReport(
        id=row.id,
        ticker=row.ticker,
        strategy=row.strategy,
        visualization=row.visualization,
        params=result.get("params") or row.params or {},
        metrics=result.get("metrics") or {},
        series=result.get("series"),
        images=result.get("images"),
        created_at=row.created_at,
    )


@router.post("/dca", response_model=BacktestReport)
def create_dca_backtest(body: BacktestRequest, db: Session = Depends(get_db)) -> BacktestReport:
    if body.end_date < body.start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")

    try:
        row = run_and_persist_dca_backtest(
            db,
            ticker=body.ticker,
            start_date=body.start_date,
            end_date=body.end_date,
            optimize=body.optimize,
            visualization=body.visualization.value,
            lookback=body.lookback,
            drawdown_thresh=body.drawdown_thresh,
            sma_period=body.sma_period,
            initial_cash=body.initial_cash,
            monthly_cash=body.monthly_cash,
            fee_rate=body.fee_rate,
        )
    except BacktestServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {exc}") from exc

    return _to_report(row)


@router.get("/runs", response_model=BacktestRunListResponse)
def list_runs(
    ticker: str | None = Query(None),
    strategy: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> BacktestRunListResponse:
    rows = list_backtest_runs(db, ticker=ticker, strategy=strategy, limit=limit, offset=offset)
    items = [
        BacktestRunSummary(
            id=row.id,
            ticker=row.ticker,
            strategy=row.strategy,
            start_date=row.start_date,
            end_date=row.end_date,
            created_at=row.created_at,
            sharpe=row.sharpe,
            cagr=row.cagr,
            total_return_pct=row.total_return_pct,
            max_drawdown_pct=row.max_drawdown_pct,
            visualization=row.visualization,
            params=row.params or {},
        )
        for row in rows
    ]
    return BacktestRunListResponse(items=items, count=len(items))


@router.get("/runs/{run_id}", response_model=BacktestReport)
def get_run(run_id: UUID, db: Session = Depends(get_db)) -> BacktestReport:
    row = get_backtest_run(db, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return _to_report(row)
