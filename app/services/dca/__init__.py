from app.services.dca.metrics import calculate_cagr, calculate_sharpe
from app.services.dca.optimize import optimize_strategy
from app.services.dca.plots import build_performance_figure, render_performance_image
from app.services.dca.report import build_metrics, build_series, build_backtest_report
from app.services.dca.scheduled import run_scheduled_dca
from app.services.dca.strategy import run_aggressive_dca, run_benchmark, run_standard_dca

__all__ = [
    "calculate_sharpe",
    "calculate_cagr",
    "run_aggressive_dca",
    "run_scheduled_dca",
    "run_standard_dca",
    "run_benchmark",
    "optimize_strategy",
    "build_performance_figure",
    "render_performance_image",
    "build_metrics",
    "build_series",
    "build_backtest_report",
]
