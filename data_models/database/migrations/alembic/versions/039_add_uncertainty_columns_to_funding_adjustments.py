"""Add uncertainty-aware buffer columns to funding_engine_adjustments

These columns capture the dynamic uncertainty metrics from the FundingModel
for validation of the uncertainty-aware pricing strategy.

Columns added:
- locked_fraction: How much of funding rate is "locked in" (0-1)
- sigma: Base uncertainty at prediction time
- sigma_total: Uncertainty scaled by sqrt(num_crossings)
- buffer: Conservative buffer applied (k × sigma_total)
- use_dynamic_uncertainty: Whether dynamic uncertainty is enabled
- num_crossings: Number of funding events crossed

Revision ID: 039
Revises: 038
Create Date: 2025-12-13 10:09:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "039"
down_revision: Union[str, None] = "038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add uncertainty columns to funding_engine_adjustments."""

    # Add columns
    op.execute(
        """
        ALTER TABLE funding_engine_adjustments
        ADD COLUMN IF NOT EXISTS locked_fraction DECIMAL(10, 6);
    """
    )
    op.execute(
        """
        ALTER TABLE funding_engine_adjustments
        ADD COLUMN IF NOT EXISTS sigma DECIMAL(18, 10);
    """
    )
    op.execute(
        """
        ALTER TABLE funding_engine_adjustments
        ADD COLUMN IF NOT EXISTS sigma_total DECIMAL(18, 10);
    """
    )
    op.execute(
        """
        ALTER TABLE funding_engine_adjustments
        ADD COLUMN IF NOT EXISTS buffer DECIMAL(18, 10);
    """
    )
    op.execute(
        """
        ALTER TABLE funding_engine_adjustments
        ADD COLUMN IF NOT EXISTS use_dynamic_uncertainty BOOLEAN DEFAULT TRUE;
    """
    )
    op.execute(
        """
        ALTER TABLE funding_engine_adjustments
        ADD COLUMN IF NOT EXISTS num_crossings INTEGER DEFAULT 0;
    """
    )

    # Add indexes for uncertainty analysis
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_adj_locked_fraction
            ON funding_engine_adjustments(locked_fraction);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_adj_buffer
            ON funding_engine_adjustments(buffer);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_adj_num_crossings
            ON funding_engine_adjustments(num_crossings);
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_funding_adj_exchange_uncertainty
            ON funding_engine_adjustments(exchange, locked_fraction, sigma);
    """
    )

    # Add column comments
    op.execute(
        """
        COMMENT ON COLUMN funding_engine_adjustments.locked_fraction IS
        'Fraction of funding rate locked in (0-1), based on time-weighted averaging quirks';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN funding_engine_adjustments.sigma IS
        'Base uncertainty σ = σ_0 × √(1 - locked) for time-weighted exchanges';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN funding_engine_adjustments.sigma_total IS
        'Total uncertainty σ_total = σ × √(num_crossings)';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN funding_engine_adjustments.buffer IS
        'Conservative buffer = k × σ_total, subtracted from funding benefit';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN funding_engine_adjustments.use_dynamic_uncertainty IS
        'True if using dynamic uncertainty model, False if using static safety_buffer';
    """
    )
    op.execute(
        """
        COMMENT ON COLUMN funding_engine_adjustments.num_crossings IS
        'Number of funding events crossed during holding period';
    """
    )


def downgrade() -> None:
    """Remove uncertainty columns from funding_engine_adjustments."""

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_funding_adj_exchange_uncertainty;")
    op.execute("DROP INDEX IF EXISTS idx_funding_adj_num_crossings;")
    op.execute("DROP INDEX IF EXISTS idx_funding_adj_buffer;")
    op.execute("DROP INDEX IF EXISTS idx_funding_adj_locked_fraction;")

    # Drop columns
    op.execute("ALTER TABLE funding_engine_adjustments DROP COLUMN IF EXISTS num_crossings;")
    op.execute("ALTER TABLE funding_engine_adjustments DROP COLUMN IF EXISTS use_dynamic_uncertainty;")
    op.execute("ALTER TABLE funding_engine_adjustments DROP COLUMN IF EXISTS buffer;")
    op.execute("ALTER TABLE funding_engine_adjustments DROP COLUMN IF EXISTS sigma_total;")
    op.execute("ALTER TABLE funding_engine_adjustments DROP COLUMN IF EXISTS sigma;")
    op.execute("ALTER TABLE funding_engine_adjustments DROP COLUMN IF EXISTS locked_fraction;")
