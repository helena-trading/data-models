"""Create graph_opportunity_snapshots table.

Revision ID: 057
Revises: 056
Create Date: 2026-02-07

Stores periodic snapshots of cross-exchange opportunity calculations
from the GraphOpportunityMonitor. Each row represents one
(maker, taker, contract, direction) combination with fee-adjusted
net spread and optional funding adjustment.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "057"
down_revision: Union[str, None] = "056"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create graph_opportunity_snapshots table with indexes."""

    op.execute(
        """
        CREATE TABLE graph_opportunity_snapshots (
            id SERIAL PRIMARY KEY,
            snapshot_time TIMESTAMPTZ NOT NULL,
            maker_exchange VARCHAR(50) NOT NULL,
            taker_exchange VARCHAR(50) NOT NULL,
            contract VARCHAR(50) NOT NULL,
            direction VARCHAR(10) NOT NULL,
            maker_price DOUBLE PRECISION,
            taker_price DOUBLE PRECISION,
            mid_price DOUBLE PRECISION,
            raw_spread_bps DOUBLE PRECISION,
            maker_fee_bps DOUBLE PRECISION,
            taker_fee_bps DOUBLE PRECISION,
            net_spread_bps DOUBLE PRECISION,
            funding_rate_maker DOUBLE PRECISION,
            funding_rate_taker DOUBLE PRECISION,
            funding_adj_1h_bps DOUBLE PRECISION,
            funding_adj_8h_bps DOUBLE PRECISION,
            net_after_funding_8h_bps DOUBLE PRECISION,
            rank INTEGER
        );
        """
    )

    op.execute("CREATE INDEX idx_graph_opp_time ON graph_opportunity_snapshots(snapshot_time);")
    op.execute("CREATE INDEX idx_graph_opp_contract ON graph_opportunity_snapshots(contract, snapshot_time);")
    op.execute("CREATE INDEX idx_graph_opp_latest ON graph_opportunity_snapshots(snapshot_time DESC, net_spread_bps DESC);")


def downgrade() -> None:
    """Drop graph_opportunity_snapshots table."""
    op.execute("DROP TABLE IF EXISTS graph_opportunity_snapshots;")
