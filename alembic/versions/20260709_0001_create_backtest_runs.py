"""create backtest_runs

Revision ID: 20260709_0001
Revises:
Create Date: 2026-07-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260709_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticker", sa.String(length=64), nullable=False),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("sharpe", sa.Float(), nullable=True),
        sa.Column("cagr", sa.Float(), nullable=True),
        sa.Column("total_return_pct", sa.Float(), nullable=True),
        sa.Column("max_drawdown_pct", sa.Float(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("visualization", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backtest_runs_ticker", "backtest_runs", ["ticker"], unique=False)
    op.create_index("ix_backtest_runs_strategy", "backtest_runs", ["strategy"], unique=False)
    op.create_index(
        "ix_backtest_runs_ticker_strategy",
        "backtest_runs",
        ["ticker", "strategy"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_backtest_runs_ticker_strategy", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_strategy", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_ticker", table_name="backtest_runs")
    op.drop_table("backtest_runs")
