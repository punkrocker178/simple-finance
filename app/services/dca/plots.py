from __future__ import annotations

import base64
import io

import matplotlib.pyplot as plt
import pandas as pd


def build_performance_figure(
    agg_dca_df: pd.DataFrame,
    std_dca_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    title_suffix: str = "",
):
    plt.style.use("seaborn-v0_8-darkgrid")
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 15))

    ax1.plot(
        benchmark_df.index,
        benchmark_df["Portfolio_Value"],
        label="Lump Sum Benchmark",
        color="gray",
        linestyle="--",
    )
    ax1.plot(
        agg_dca_df.index,
        agg_dca_df["Portfolio_Value"],
        label="Aggressive DCA (Drawdown Dips)",
        color="blue",
    )
    ax1.plot(
        std_dca_df.index,
        std_dca_df["Portfolio_Value"],
        label="Standard DCA (Equal Tranches)",
        color="orange",
    )

    dip_dates = agg_dca_df[agg_dca_df["Execution_Signal"]].index
    dip_prices = agg_dca_df.loc[dip_dates, "Portfolio_Value"]
    ax1.scatter(
        dip_dates,
        dip_prices,
        color="red",
        marker="^",
        label="Dip Buy Triggered (+2M)",
        zorder=5,
    )

    ax1.set_title(f"Active Portfolio Value Growth {title_suffix}")
    ax1.set_ylabel("VND")
    ax1.legend()
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _p: format(int(x), ",")))

    agg_peak = agg_dca_df["Portfolio_Value"].cummax()
    agg_dd = (agg_dca_df["Portfolio_Value"] - agg_peak) / agg_peak * 100

    std_peak = std_dca_df["Portfolio_Value"].cummax()
    std_dd = (std_dca_df["Portfolio_Value"] - std_peak) / std_peak * 100

    bench_peak = benchmark_df["Portfolio_Value"].cummax()
    bench_dd = (benchmark_df["Portfolio_Value"] - bench_peak) / bench_peak * 100

    ax2.fill_between(
        agg_dd.index, agg_dd, 0, color="blue", alpha=0.2, label="Aggressive DCA Drawdown"
    )
    ax2.plot(std_dd.index, std_dd, color="orange", linewidth=1.5, label="Standard DCA Drawdown")
    ax2.plot(
        bench_dd.index,
        bench_dd,
        color="gray",
        linestyle="--",
        linewidth=1,
        label="Lump Sum Drawdown",
    )

    ax2.set_title("Daily Drawdown Profile (%)")
    ax2.set_ylabel("Drawdown (%)")
    ax2.legend()

    agg_monthly = agg_dca_df["Portfolio_Value"].resample("ME").last().pct_change().fillna(0) * 100
    std_monthly = std_dca_df["Portfolio_Value"].resample("ME").last().pct_change().fillna(0) * 100
    bench_monthly = (
        benchmark_df["Portfolio_Value"].resample("ME").last().pct_change().fillna(0) * 100
    )

    monthly_df = pd.DataFrame(
        {"Aggressive DCA": agg_monthly, "Standard DCA": std_monthly, "Lump Sum": bench_monthly}
    )
    monthly_df.index = monthly_df.index.strftime("%Y-%m")

    monthly_df.plot(kind="bar", ax=ax3, color=["blue", "orange", "gray"], alpha=0.8)
    ax3.set_title("Monthly Portfolio Growth (%) - Includes Cash Injections")
    ax3.set_ylabel("Return (%)")
    ax3.set_xlabel("Month")
    ax3.legend(loc="upper left")

    n = max(1, len(monthly_df) // 15)
    ax3.set_xticks(range(0, len(monthly_df), n))
    ax3.set_xticklabels(monthly_df.index[::n], rotation=45)

    fig.tight_layout()
    return fig


def render_performance_image(
    agg_dca_df: pd.DataFrame,
    std_dca_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    title_suffix: str = "",
) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg", force=False)
    fig = build_performance_figure(agg_dca_df, std_dca_df, benchmark_df, title_suffix=title_suffix)
    buffer = io.BytesIO()
    try:
        fig.savefig(buffer, format="png", dpi=120, bbox_inches="tight")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    finally:
        plt.close(fig)
    return {"content_type": "image/png", "base64": encoded}


def show_performance(
    agg_dca_df: pd.DataFrame,
    std_dca_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    title_suffix: str = "",
) -> None:
    """CLI helper: build figure and display interactively when a GUI backend is available."""
    fig = build_performance_figure(agg_dca_df, std_dca_df, benchmark_df, title_suffix=title_suffix)
    plt.show()
    plt.close(fig)
