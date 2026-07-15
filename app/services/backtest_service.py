from __future__ import annotations

import logging
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
from app.services.dca.scheduled import run_scheduled_dca
from app.services.dca.strategy import run_aggressive_dca, run_benchmark, run_standard_dca
from app.services.market_data.base import MarketDataProvider
from app.services.market_data.factory import get_market_data_provider
from app.services.market_data.common import MarketDataError

logger = logging.getLogger(__name__)


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
    strategy: str = "aggressive_dca",
    cadence: str = "monthly",
    day_of_month: int = 1,
    weekday: int = 0,
    skip_after_buy_n: int = 0,
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

    logger.info("Fetching market data for %s (%s to %s)", symbol, start_date, end_date)
    try:
        df = fetch_data(
            symbol,
            start_date.isoformat(),
            end_date.isoformat(),
            provider=provider,
        )
    except MarketDataError as exc:
        logger.error("Failed to fetch market data for %s: %s", symbol, exc)
        raise BacktestServiceError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch market data for %s", symbol)
        raise BacktestServiceError(f"Failed to fetch market data: {exc}") from exc

    if df.empty:
        logger.warning("No market data for %s in range %s to %s", symbol, start_date, end_date)
        raise BacktestServiceError(f"No market data for {symbol} in the requested range.")

    logger.info("Fetched %d rows for %s", len(df), symbol)

    params: dict[str, Any]
    title_suffix = ""
    primary_key = "aggressive_dca"
    primary_label = "Aggressive DCA"

    if strategy == "scheduled_dca":
        params = {
            "cadence": cadence,
            "day_of_month": day_of_month,
            "weekday": weekday,
            "skip_after_buy_n": skip_after_buy_n,
            "initial_cash": cash0,
            "monthly_cash": cash_m,
            "fee_rate": fee,
            "optimized": False,
        }
        logger.info("Running scheduled DCA for %s with params %s", symbol, params)
        try:
            primary_df, _ = run_scheduled_dca(
                df,
                initial_cash=cash0,
                monthly_cash=cash_m,
                fee_rate=fee,
                cadence=cadence,
                day_of_month=day_of_month,
                weekday=weekday,
                skip_after_buy_n=skip_after_buy_n,
                annual_rf_rate=rf,
            )
        except ValueError as exc:
            raise BacktestServiceError(str(exc)) from exc
        primary_key = "scheduled_dca"
        primary_label = "Scheduled DCA"
    elif optimize:
        logger.info("Starting strategy optimization for %s", symbol)
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
        logger.info(
            "Optimization complete for %s: lookback=%s drawdown_thresh=%s sma_period=%s in_sample_sharpe=%s",
            symbol,
            params["lookback"],
            params["drawdown_thresh"],
            params["sma_period"],
            params.get("in_sample_sharpe"),
        )
        logger.info("Running backtest for %s with params %s", symbol, params)
        primary_df, _ = run_aggressive_dca(
            run_df,
            lookback=params["lookback"],
            drawdown_thresh=params["drawdown_thresh"],
            sma_period=params["sma_period"],
            initial_cash=cash0,
            monthly_cash=cash_m,
            fee_rate=fee,
            annual_rf_rate=rf,
        )
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
        logger.info("Using fixed parameters for %s: %s", symbol, params)
        logger.info("Running backtest for %s with params %s", symbol, params)
        primary_df, _ = run_aggressive_dca(
            run_df,
            lookback=params["lookback"],
            drawdown_thresh=params["drawdown_thresh"],
            sma_period=params["sma_period"],
            initial_cash=cash0,
            monthly_cash=cash_m,
            fee_rate=fee,
            annual_rf_rate=rf,
        )

    if primary_df is None or primary_df.empty:
        logger.warning("Test period too small after indicator warmup for %s", symbol)
        raise BacktestServiceError("Test period too small after indicator warmup.")

    logger.info(
        "%s complete for %s (%d rows); running standard DCA and benchmark",
        primary_label,
        symbol,
        len(primary_df),
    )
    std_df = run_standard_dca(primary_df, fee_rate=fee)
    bench_df = run_benchmark(primary_df, fee_rate=fee)

    logger.info("Building backtest report for %s (visualization=%s%s)", symbol, visualization, f" {title_suffix}" if title_suffix else "")
    report = build_backtest_report(
        primary_df,
        std_df,
        bench_df,
        params=params,
        visualization=visualization,
        annual_rf_rate=rf,
        title_suffix=title_suffix,
        primary_key=primary_key,
        primary_label=primary_label,
    )

    metrics = report["metrics"][primary_key]
    logger.info(
        "Persisting backtest run for %s: sharpe=%.4f cagr=%.2f%% total_return=%.2f%%",
        symbol,
        metrics["sharpe_ratio"],
        metrics["cagr_pct"],
        metrics["total_return_pct"],
    )
    row = BacktestRun(
        ticker=symbol,
        strategy=primary_key,
        start_date=start_date,
        end_date=end_date,
        sharpe=metrics["sharpe_ratio"],
        cagr=metrics["cagr_pct"],
        total_return_pct=metrics["total_return_pct"],
        max_drawdown_pct=metrics["max_drawdown_pct"],
        params=params,
        result=report,
        visualization=visualization,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("Saved backtest run id=%s for %s", row.id, symbol)
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
