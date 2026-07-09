from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.backtest_run import BacktestRun
from app.services.dca.data import fetch_data
from app.services.dca.optimize import optimize_strategy
from app.services.dca.report import VisualizationMode, build_backtest_report
from app.services.dca.strategy import run_aggressive_dca, run_benchmark, run_standard_dca
from app.services.market_data.base import MarketDataProvider
from app.services.market_data.factory import get_market_data_provider
from app.services.market_data.yfinance_client import MarketDataError


class BacktestServiceError(Exception):
    pass


def run_and_persist_dca_backtest(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    ticker: str | None = None,
    optimize: bool = True,
    visualization: VisualizationMode = "series",
    lookback: int | None = None,
    drawdown_thresh: float | None = None,
    sma_period: int | None = None,
    initial_cash: float | None = None,
    monthly_cash: float | None = None,
    fee_rate: float | None = None,
    settings: Settings | None = None,
    provider: MarketDataProvider | None = None,
) -> BacktestRun:
    settings = settings or get_settings()
    provider = provider or get_market_data_provider(settings)
    symbol = ticker or settings.default_ticker

    cash0 = initial_cash if initial_cash is not None else settings.default_initial_cash
    cash_m = monthly_cash if monthly_cash is not None else settings.default_monthly_cash
    fee = fee_rate if fee_rate is not None else settings.default_fee_rate
    rf = settings.annual_rf_rate

    try:
        df = fetch_data(
            symbol,
            start_date.isoformat(),
            end_date.isoformat(),
            provider=provider,
        )
    except MarketDataError as exc:
        raise BacktestServiceError(str(exc)) from exc
    except Exception as exc:
        raise BacktestServiceError(f"Failed to fetch market data: {exc}") from exc

    if df.empty:
        raise BacktestServiceError(f"No market data for {symbol} in the requested range.")

    params: dict[str, Any]
    title_suffix = ""

    if optimize:
        best_params, _in_sample, out_of_sample = optimize_strategy(
            df,
            initial_cash=cash0,
            monthly_cash=cash_m,
            fee_rate=fee,
            annual_rf_rate=rf,
        )
        params = {
            "lookback": best_params["lookback"],
            "drawdown_thresh": best_params["drawdown_thresh"],
            "sma_period": best_params["sma_period"],
            "optimized": True,
            "in_sample_sharpe": best_params.get("in_sample_sharpe"),
            "initial_cash": cash0,
            "monthly_cash": cash_m,
            "fee_rate": fee,
        }
        run_df = out_of_sample
        title_suffix = "(Out-of-Sample)"
    else:
        params = {
            "lookback": lookback if lookback is not None else 100,
            "drawdown_thresh": drawdown_thresh if drawdown_thresh is not None else 0.15,
            "sma_period": sma_period if sma_period is not None else 200,
            "optimized": False,
            "initial_cash": cash0,
            "monthly_cash": cash_m,
            "fee_rate": fee,
        }
        run_df = df

    agg_df, _ = run_aggressive_dca(
        run_df,
        lookback=params["lookback"],
        drawdown_thresh=params["drawdown_thresh"],
        sma_period=params["sma_period"],
        initial_cash=cash0,
        monthly_cash=cash_m,
        fee_rate=fee,
        annual_rf_rate=rf,
    )

    if agg_df is None or agg_df.empty:
        raise BacktestServiceError("Test period too small after indicator warmup.")

    std_df = run_standard_dca(agg_df, fee_rate=fee)
    bench_df = run_benchmark(agg_df, fee_rate=fee)

    report = build_backtest_report(
        agg_df,
        std_df,
        bench_df,
        params=params,
        visualization=visualization,
        annual_rf_rate=rf,
        title_suffix=title_suffix,
    )

    agg_metrics = report["metrics"]["aggressive_dca"]
    row = BacktestRun(
        ticker=symbol,
        strategy="aggressive_dca",
        start_date=start_date,
        end_date=end_date,
        sharpe=agg_metrics["sharpe_ratio"],
        cagr=agg_metrics["cagr_pct"],
        total_return_pct=agg_metrics["total_return_pct"],
        max_drawdown_pct=agg_metrics["max_drawdown_pct"],
        params=params,
        result=report,
        visualization=visualization,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_backtest_runs(
    db: Session,
    *,
    ticker: str | None = None,
    strategy: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[BacktestRun]:
    stmt = select(BacktestRun).order_by(BacktestRun.created_at.desc())
    if ticker:
        stmt = stmt.where(BacktestRun.ticker == ticker)
    if strategy:
        stmt = stmt.where(BacktestRun.strategy == strategy)
    stmt = stmt.offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


def get_backtest_run(db: Session, run_id: UUID) -> BacktestRun | None:
    return db.get(BacktestRun, run_id)
