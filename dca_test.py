"""CLI entrypoint for Aggressive DCA backtests (uses the app package)."""

from app.services.dca.data import fetch_data
from app.services.dca.optimize import optimize_strategy
from app.services.dca.plots import show_performance
from app.services.dca.report import build_metrics
from app.services.dca.strategy import run_aggressive_dca, run_benchmark, run_standard_dca


def print_report(agg_dca_df, std_dca_df, benchmark_df, phase_name: str) -> None:
    print(f"\n--- PERFORMANCE METRICS: {phase_name} ---")
    metrics = build_metrics(agg_dca_df, std_dca_df, benchmark_df)

    def fmt(m):
        return [
            f"{m['total_cash_injected']:,.0f}",
            f"{m['final_portfolio_value']:,.0f}",
            f"{m['total_return_pct']:.2f}%",
            f"{m['cagr_pct']:.2f}%",
            f"{m['max_drawdown_pct']:.2f}%",
            f"{m['sharpe_ratio']:.2f}",
            m["dip_buys_triggered"] if m["dip_buys_triggered"] is not None else "N/A",
        ]

    a, s, b = fmt(metrics["aggressive_dca"]), fmt(metrics["standard_dca"]), fmt(metrics["lump_sum"])
    table = f"""
| Metric                          | Aggressive DCA | Standard DCA | Lump Sum Benchmark |
|---------------------------------|----------------|--------------|--------------------|
| Total Cash Injected (VND)       | {a[0]} | {s[0]} | {b[0]} |
| Final Portfolio Value (VND)     | {a[1]} | {s[1]} | {b[1]} |
| Total Return on Cash (%)        | {a[2]} | {s[2]} | {b[2]} |
| CAGR (%)                        | {a[3]} | {s[3]} | {b[3]} |
| Maximum Drawdown (%)            | {a[4]} | {s[4]} | {b[4]} |
| Sharpe Ratio                    | {a[5]} | {s[5]} | {b[5]} |
| Drawdown Dip Buys Triggered     | {a[6]} | N/A | N/A |
    """
    print(table)


if __name__ == "__main__":
    TICKER = "E1VFVN30.VN"
    df = fetch_data(TICKER, "2016-01-01", "2025-12-31")

    best_params, _in_sample, out_of_sample = optimize_strategy(df)
    print(
        f"Best Params: Lookback={best_params['lookback']} days, "
        f"Drawdown=-{best_params['drawdown_thresh'] * 100}%, "
        f"SMA={best_params['sma_period']} "
        f"(IS Sharpe: {best_params.get('in_sample_sharpe', 0):.2f})"
    )

    print("\nRunning Out-of-Sample Test with optimized parameters...")
    oos_agg_dca, _ = run_aggressive_dca(
        out_of_sample,
        lookback=best_params["lookback"],
        drawdown_thresh=best_params["drawdown_thresh"],
        sma_period=best_params["sma_period"],
    )

    if oos_agg_dca is not None and not oos_agg_dca.empty:
        oos_std_dca = run_standard_dca(oos_agg_dca)
        oos_bench = run_benchmark(oos_agg_dca)
        print_report(oos_agg_dca, oos_std_dca, oos_bench, "OUT-OF-SAMPLE")
        show_performance(oos_agg_dca, oos_std_dca, oos_bench, "(Out-of-Sample)")
    else:
        print("Error: Test period still too small after indicator warmup.")
