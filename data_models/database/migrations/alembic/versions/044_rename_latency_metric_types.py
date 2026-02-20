"""Rename latency metric types to be more explicit.

Revision ID: 044_rename_latency_metric_types
Revises: 043_add_bot_client_to_latency_metrics
Create Date: 2025-01-18

Old names were ambiguous:
- 'orderbook' -> 'maker_orderbook_fetch': Time to fetch orderbook from maker exchange
- 'placement' -> 'maker_order_ack': Time from sending maker order to exchange acknowledgment
- 'cancellation' -> 'cancel_request_send': Time from cancel initiation to cancel request sent
- 'cycle' -> 'trade_cycle': Total time from maker fill to taker fill completion
- 'fill_notification' -> 'maker_fill_ws_delay': Time from exchange fill to WebSocket notification
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "044"
down_revision: Union[str, None] = "043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename metric types to more explicit names."""
    # Update existing metric_type values to new names
    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'maker_orderbook_fetch'
        WHERE metric_type = 'orderbook';
    """
    )

    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'maker_order_ack'
        WHERE metric_type = 'placement';
    """
    )

    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'cancel_request_send'
        WHERE metric_type = 'cancellation';
    """
    )

    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'trade_cycle'
        WHERE metric_type = 'cycle';
    """
    )

    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'maker_fill_ws_delay'
        WHERE metric_type = 'fill_notification';
    """
    )


def downgrade() -> None:
    """Revert to old metric type names."""
    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'orderbook'
        WHERE metric_type = 'maker_orderbook_fetch';
    """
    )

    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'placement'
        WHERE metric_type = 'maker_order_ack';
    """
    )

    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'cancellation'
        WHERE metric_type = 'cancel_request_send';
    """
    )

    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'cycle'
        WHERE metric_type = 'trade_cycle';
    """
    )

    op.execute(
        """
        UPDATE latency_metrics
        SET metric_type = 'fill_notification'
        WHERE metric_type = 'maker_fill_ws_delay';
    """
    )
