"""Create funding predictions table for model validation

Tracks funding rate predictions vs actual outcomes to validate
the uncertainty-aware pricing model and calibrate parameters.

Note: bot_id is a logical reference only (no FK - bots table is in credentials DB)

Revision ID: 038
Revises: 037
Create Date: 2025-12-13 09:53:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "038"
down_revision: Union[str, None] = "037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create funding_predictions table."""

    # Create funding_predictions table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS funding_predictions (
            id SERIAL PRIMARY KEY,

            -- When the prediction was made
            prediction_time TIMESTAMP WITH TIME ZONE NOT NULL,

            -- Identifiers
            exchange VARCHAR(100) NOT NULL,
            contract VARCHAR(50) NOT NULL,
            bot_id INTEGER,  -- Logical reference to bots.id (no FK - cross-database)
            trade_id VARCHAR(100),  -- Links to block_trade.block_id if applicable

            -- Prediction inputs
            funding_rate DECIMAL(18, 10) NOT NULL,  -- Rate used for prediction
            time_to_next_hours DECIMAL(10, 4) NOT NULL,  -- Hours to next funding
            interval_hours DECIMAL(10, 4) NOT NULL,  -- Funding interval (1h or 8h)
            horizon_hours DECIMAL(10, 4) NOT NULL,  -- Expected holding time

            -- Prediction outputs
            predicted_crossings INTEGER NOT NULL,  -- Expected funding events
            predicted_pnl_long DECIMAL(18, 10) NOT NULL,  -- Expected PnL for long
            predicted_pnl_short DECIMAL(18, 10) NOT NULL,  -- Expected PnL for short

            -- Uncertainty metrics (for model validation)
            locked_fraction DECIMAL(10, 6) NOT NULL DEFAULT 0,
            sigma DECIMAL(18, 10) NOT NULL DEFAULT 0,
            buffer DECIMAL(18, 10) NOT NULL DEFAULT 0,

            -- Actual outcomes (updated after position closes)
            actual_crossings INTEGER,
            actual_pnl DECIMAL(18, 10),
            actual_holding_hours DECIMAL(10, 4),
            position_side VARCHAR(10),  -- 'long' or 'short'

            -- Computed errors (populated when actual values are known)
            crossing_error INTEGER,
            pnl_error DECIMAL(18, 10),
            pnl_error_pct DECIMAL(10, 6),

            -- Status tracking
            status VARCHAR(20) NOT NULL DEFAULT 'pending',

            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """
    )

    # Indexes
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_pred_time
            ON funding_predictions(prediction_time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_pred_exchange_contract
            ON funding_predictions(exchange, contract);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_pred_exchange_contract_time
            ON funding_predictions(exchange, contract, prediction_time);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_pred_status
            ON funding_predictions(status);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_pred_bot_id
            ON funding_predictions(bot_id)
            WHERE bot_id IS NOT NULL;
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_pred_trade_id
            ON funding_predictions(trade_id)
            WHERE trade_id IS NOT NULL;
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_pred_pnl_error
            ON funding_predictions(pnl_error)
            WHERE pnl_error IS NOT NULL;
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_pred_locked_fraction
            ON funding_predictions(locked_fraction);
    """
    )

    # Trigger for updated_at
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_funding_predictions_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trigger_funding_predictions_updated_at ON funding_predictions;
    """
    )
    op.execute(
        """
        CREATE TRIGGER trigger_funding_predictions_updated_at
            BEFORE UPDATE ON funding_predictions
            FOR EACH ROW
            EXECUTE FUNCTION update_funding_predictions_timestamp();
    """
    )

    # Comments
    op.execute(
        """
        COMMENT ON TABLE funding_predictions IS
        'Tracks funding rate predictions vs actual outcomes for uncertainty model validation';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN funding_predictions.bot_id IS
        'Logical reference to bots.id (no FK - cross-database reference to credentials DB)';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN funding_predictions.locked_fraction IS
        'How much of funding rate was locked in (0-1, based on time-weighted averaging)';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN funding_predictions.sigma IS
        'Uncertainty (σ) at prediction time, used for conservative buffer';
    """
    )


def downgrade() -> None:
    """Drop funding_predictions table."""

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_funding_predictions_updated_at ON funding_predictions;")
    op.execute("DROP FUNCTION IF EXISTS update_funding_predictions_timestamp();")

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_funding_pred_locked_fraction;")
    op.execute("DROP INDEX IF EXISTS idx_funding_pred_pnl_error;")
    op.execute("DROP INDEX IF EXISTS idx_funding_pred_trade_id;")
    op.execute("DROP INDEX IF EXISTS idx_funding_pred_bot_id;")
    op.execute("DROP INDEX IF EXISTS idx_funding_pred_status;")
    op.execute("DROP INDEX IF EXISTS idx_funding_pred_exchange_contract_time;")
    op.execute("DROP INDEX IF EXISTS idx_funding_pred_exchange_contract;")
    op.execute("DROP INDEX IF EXISTS idx_funding_pred_time;")

    # Drop table
    op.execute("DROP TABLE IF EXISTS funding_predictions;")
