"""Create signal logging tables for quote decisions and fill outcomes

This migration creates:
1. quote_decision_logs - Every quote decision from SignalProcessor
2. fill_outcome_logs - Actual fill/cancel outcomes linked to decisions

These tables enable:
- Fill probability model calibration (compare predicted vs actual fills)
- Expected value analysis (compare EV estimates to realized profits)
- ML training data collection for future model improvements

Revision ID: 041
Revises: 040
Create Date: 2025-12-22 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "041"
down_revision: Union[str, None] = "040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create signal logging tables."""

    # 1. Create quote_decision_logs table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS quote_decision_logs (
            id SERIAL PRIMARY KEY,
            time TIMESTAMPTZ NOT NULL,
            bot_id INTEGER NOT NULL,
            route_id VARCHAR(50) NOT NULL,
            contract VARCHAR(50) NOT NULL,
            internal_id VARCHAR(50) NOT NULL,

            -- Decision output
            action VARCHAR(20) NOT NULL,  -- 'quote', 'quote_wide', 'skip'
            proposed_price NUMERIC(30, 10) NOT NULL,
            adjusted_price NUMERIC(30, 10),
            is_bid BOOLEAN NOT NULL,

            -- Signal scores
            fill_probability NUMERIC(10, 6) NOT NULL,
            expected_value_bps NUMERIC(12, 6) NOT NULL,

            -- Fair value context
            fair_mid NUMERIC(30, 10) NOT NULL,
            fair_bid NUMERIC(30, 10) NOT NULL,
            fair_ask NUMERIC(30, 10) NOT NULL,
            funding_shift_bps NUMERIC(12, 6),
            confidence NUMERIC(6, 4),

            -- Market features
            volatility_1m NUMERIC(12, 8),
            volatility_5m NUMERIC(12, 8),
            spread_bps NUMERIC(12, 6),
            imbalance NUMERIC(8, 6),
            depth_bid_usd NUMERIC(20, 2),
            depth_ask_usd NUMERIC(20, 2),
            orderbook_age_ms INTEGER,

            -- Metadata
            reason VARCHAR(100),
            features_snapshot JSONB,
            decision_time_ns BIGINT,
            wide_spread_adjustment_bps NUMERIC(10, 4),

            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Indexes for quote_decision_logs
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quote_decision_logs_time
        ON quote_decision_logs(time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quote_decision_logs_bot_id
        ON quote_decision_logs(bot_id);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quote_decision_logs_bot_contract_time
        ON quote_decision_logs(bot_id, contract, time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quote_decision_logs_internal_id
        ON quote_decision_logs(internal_id);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quote_decision_logs_action
        ON quote_decision_logs(action);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quote_decision_logs_route_time
        ON quote_decision_logs(route_id, time);
    """
    )

    # 2. Create fill_outcome_logs table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fill_outcome_logs (
            id SERIAL PRIMARY KEY,
            time TIMESTAMPTZ NOT NULL,
            internal_id VARCHAR(50) NOT NULL,
            bot_id INTEGER NOT NULL,
            contract VARCHAR(50) NOT NULL,

            -- Outcome
            outcome VARCHAR(30) NOT NULL,  -- 'filled', 'partially_filled', 'cancelled', 'expired'
            predicted_fill_prob NUMERIC(10, 6) NOT NULL,

            -- Fill details
            fill_time_ms INTEGER,
            filled_price NUMERIC(30, 10),
            filled_quantity NUMERIC(30, 10),
            slippage_bps NUMERIC(12, 6),
            fees_paid NUMERIC(20, 10),
            realized_pnl NUMERIC(20, 10),

            -- References
            exchange_order_id VARCHAR(100),
            quoted_price NUMERIC(30, 10),
            order_ttl_ms INTEGER,

            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """
    )

    # Indexes for fill_outcome_logs
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fill_outcome_logs_time
        ON fill_outcome_logs(time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fill_outcome_logs_internal_id
        ON fill_outcome_logs(internal_id);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fill_outcome_logs_bot_id
        ON fill_outcome_logs(bot_id);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fill_outcome_logs_outcome
        ON fill_outcome_logs(outcome);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fill_outcome_logs_bot_contract_time
        ON fill_outcome_logs(bot_id, contract, time);
    """
    )

    # Table comments
    op.execute(
        """
        COMMENT ON TABLE quote_decision_logs IS
        'Quote decisions from SignalProcessor. Links internal_id to fill_outcome_logs for calibration analysis.';
    """
    )
    op.execute(
        """
        COMMENT ON TABLE fill_outcome_logs IS
        'Fill outcomes linked to quote decisions. Used for fill probability model calibration.';
    """
    )

    # Useful comments on key columns
    op.execute(
        """
        COMMENT ON COLUMN quote_decision_logs.internal_id IS
        'Unique ID linking decision to order lifecycle. Join with fill_outcome_logs.internal_id.';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN quote_decision_logs.fill_probability IS
        'Predicted fill probability from HazardFillModel (0-1).';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN fill_outcome_logs.predicted_fill_prob IS
        'Copied from quote_decision_logs for easy calibration queries.';
    """
    )


def downgrade() -> None:
    """Drop signal logging tables.

    Note: This is a destructive operation. All signal logging data will be lost.
    """

    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_fill_outcome_logs_bot_contract_time;")
    op.execute("DROP INDEX IF EXISTS idx_fill_outcome_logs_outcome;")
    op.execute("DROP INDEX IF EXISTS idx_fill_outcome_logs_bot_id;")
    op.execute("DROP INDEX IF EXISTS idx_fill_outcome_logs_internal_id;")
    op.execute("DROP INDEX IF EXISTS idx_fill_outcome_logs_time;")

    op.execute("DROP INDEX IF EXISTS idx_quote_decision_logs_route_time;")
    op.execute("DROP INDEX IF EXISTS idx_quote_decision_logs_action;")
    op.execute("DROP INDEX IF EXISTS idx_quote_decision_logs_internal_id;")
    op.execute("DROP INDEX IF EXISTS idx_quote_decision_logs_bot_contract_time;")
    op.execute("DROP INDEX IF EXISTS idx_quote_decision_logs_bot_id;")
    op.execute("DROP INDEX IF EXISTS idx_quote_decision_logs_time;")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS fill_outcome_logs;")
    op.execute("DROP TABLE IF EXISTS quote_decision_logs;")
