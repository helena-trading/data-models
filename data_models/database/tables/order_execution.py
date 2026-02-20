"""Order execution database model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from psycopg.types.json import Jsonb

from data_models.logging import debug, error, warning
from data_models.database.types.persistence_protocols import OrderLike


@dataclass
class OrderExecution:
    """Order execution record for database storage."""

    time: datetime
    exchange: str
    contract: str
    order_id: Optional[str] = None  # VARCHAR(100) - supports UUIDs and numeric IDs
    internal_id: Optional[str] = None
    side: Optional[str] = None
    price: Optional[Decimal] = None
    size: Optional[Decimal] = None
    filled_size: Optional[Decimal] = None
    status: Optional[str] = None
    order_type: Optional[str] = None
    fees: Optional[Decimal] = None
    route_id: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = field(default_factory=dict)
    # New fields for Orders API
    bot_id: Optional[int] = None
    average_fill_price: Optional[Decimal] = None
    execution_time_ms: Optional[int] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    block_id: Optional[str] = None  # UUID stored as string
    has_any_execution: bool = False  # TRUE if order had any fills (filled_quantity > 0)

    @staticmethod
    def _extract_fees(raw_exchange_data: Optional[Dict[str, Any]]) -> Optional[Decimal]:
        """Extract fees from raw exchange data.

        Order model doesn't have a direct fees field - fees are stored in raw_exchange_data.

        Args:
            raw_exchange_data: Raw response from exchange

        Returns:
            Decimal fee amount or None if not available
        """
        if not raw_exchange_data or not isinstance(raw_exchange_data, dict):
            return None
        fee_value = raw_exchange_data.get("fee", raw_exchange_data.get("fees", 0))
        if fee_value:
            return Decimal(str(fee_value))
        return None

    @classmethod
    def from_order(
        cls,
        order: OrderLike,
        exchange: str,
        route_id: Optional[int] = None,
        bot_id: Optional[int] = None,
        block_id: Optional[str] = None,
    ) -> "OrderExecution":
        """Create from Order model.

        Args:
            order: Order object to convert
            exchange: Exchange name
            route_id: Legacy route ID (typically same as bot_id)
            bot_id: Bot ID for this order
            block_id: UUID of the block trade this order belongs to
        """
        # Log order details for debugging
        order_id_display = str(order.exchange_order_id) if order.exchange_order_id else str(order.internal_id)
        debug(
            f"[OrderExecution] Creating from Order: exchange_order_id={order.exchange_order_id}, "
            f"internal_id={order.internal_id}, display_id={order_id_display}, status={order.status}"
        )

        # Convert raw_response to ensure all enums are serializable
        raw_response = order.raw_exchange_data or {}

        # If raw_response contains enum values, convert them to strings
        if raw_response:

            def convert_enums(obj: Any) -> Any:
                """Recursively convert enum values to strings."""
                if isinstance(obj, Enum):
                    return obj.value
                elif isinstance(obj, dict):
                    return {k: convert_enums(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_enums(item) for item in obj]
                else:
                    return obj

            raw_response = convert_enums(raw_response)

        try:
            # Handle order_id conversion carefully
            # Use exchange_order_id if available, otherwise fall back to internal_id
            order_id_value = None
            if order.exchange_order_id is not None:
                # Use exchange_order_id as string (supports UUIDs, numeric IDs, etc.)
                exchange_id_str = str(order.exchange_order_id).strip()
                if exchange_id_str:
                    order_id_value = exchange_id_str

            # Fall back to internal_id if exchange_order_id is not available
            if order_id_value is None and order.internal_id is not None:
                order_id_value = str(order.internal_id)

            # Get internal_id as string
            internal_id_str = str(order.internal_id) if order.internal_id else None

            # Determine status string
            status_str = order.status if isinstance(order.status, str) else (order.status.value if order.status else None)

            # Calculate filled_at timestamp if order is filled
            filled_at_timestamp = None
            execution_time = None
            if status_str and status_str.lower() in ["filled", "completely_filled"]:
                filled_at_timestamp = datetime.now(tz=timezone.utc)  # ← FIX: Make timezone-aware
                # Calculate execution time if we have order timestamp
                if order.timestamp is not None and order.timestamp > 0:
                    # order.timestamp is in milliseconds
                    order_created_at = datetime.fromtimestamp(order.timestamp / 1000, tz=timezone.utc)
                    execution_time = int((filled_at_timestamp - order_created_at).total_seconds() * 1000)
                    # Sanity check: execution time should be positive and reasonable (< 1 hour)
                    if execution_time < 0 or execution_time > 3600000:
                        warning(
                            f"[OrderExecution] Calculated unusual execution time {execution_time}ms for order {order_id_display}. "
                            f"Order timestamp: {order.timestamp}, filled_at: {filled_at_timestamp}"
                        )
                        execution_time = None

            # Calculate cancelled_at timestamp if order is cancelled
            cancelled_at_timestamp = None
            if status_str and status_str.lower() in ["cancelled", "canceled"]:
                cancelled_at_timestamp = datetime.now(tz=timezone.utc)  # ← FIX: Make timezone-aware

            # Get average fill price
            avg_fill_price = None
            if order.avg_price is not None and order.avg_price > 0:
                avg_fill_price = Decimal(str(order.avg_price))
            elif order.filled_amount is not None and order.filled_amount > 0:
                # If avg_price not available but order is filled, use order price as approximation
                avg_fill_price = Decimal(str(order.price)) if order.price is not None else None

            # Calculate has_any_execution flag
            has_any_execution = order.filled_amount is not None and order.filled_amount > 0

            return cls(
                time=datetime.now(tz=timezone.utc),  # ← FIX: Make timezone-aware
                exchange=exchange,
                contract=order.contract,
                order_id=order_id_value,
                internal_id=internal_id_str,
                side=(order.side if isinstance(order.side, str) else (order.side.value if order.side else None)),
                price=Decimal(str(order.price)) if order.price is not None else None,
                size=Decimal(str(order.amount)) if order.amount is not None else None,
                filled_size=(Decimal(str(order.filled_amount)) if order.filled_amount is not None else None),
                status=status_str,
                order_type=(
                    order.order_type
                    if isinstance(order.order_type, str)
                    else (order.order_type.value if order.order_type else None)
                ),
                # Order doesn't have a fees field - extract from raw_exchange_data
                fees=cls._extract_fees(order.raw_exchange_data),
                route_id=route_id,
                raw_response=raw_response,
                # New fields for Orders API
                bot_id=bot_id or route_id,  # Use bot_id if provided, otherwise fall back to route_id
                average_fill_price=avg_fill_price,
                execution_time_ms=execution_time,  # Calculated from order.timestamp to filled_at
                filled_at=filled_at_timestamp,
                cancelled_at=cancelled_at_timestamp,
                block_id=block_id,
                has_any_execution=has_any_execution,
            )
        except Exception as e:
            # Use exchange_order_id if available, else internal_id for error logging
            display_order_id = str(order.exchange_order_id) if order.exchange_order_id else str(order.internal_id)
            error(
                f"[OrderExecution] Failed to create OrderExecution: {str(e)}\n"
                f"Order details: exchange_order_id={order.exchange_order_id}, internal_id={order.internal_id}, "
                f"display_id={display_order_id}, exchange={exchange}, route_id={route_id}, bot_id={bot_id}"
            )
            raise

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters."""
        query = """
            INSERT INTO order_executions
            (time, exchange, contract, order_id, internal_id,
             side, price, quantity, filled_quantity, status, order_type,
             fee, route_id, metadata, bot_id, average_fill_price,
             execution_time_ms, filled_at, cancelled_at, block_id, has_any_execution)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.time,
            self.exchange,
            self.contract,
            self.order_id,
            self.internal_id,
            self.side,
            self.price,
            self.size,  # maps to quantity column
            self.filled_size,  # maps to filled_quantity column
            self.status,
            self.order_type,
            self.fees,  # maps to fee column
            self.route_id,
            (Jsonb(self.raw_response) if self.raw_response else None),  # maps to metadata column
            # New fields for Orders API
            self.bot_id,
            self.average_fill_price,
            self.execution_time_ms,
            self.filled_at,
            self.cancelled_at,
            self.block_id,
            self.has_any_execution,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts.

        Note: Duplicate handling is done via exception catching in writer.py
        because the UNIQUE index is partial (WHERE internal_id IS NOT NULL)
        and PostgreSQL doesn't support ON CONFLICT with partial indexes.
        """
        return """
            INSERT INTO order_executions
            (time, exchange, contract, order_id, internal_id,
             side, price, quantity, filled_quantity, status, order_type,
             fee, route_id, metadata, bot_id, average_fill_price,
             execution_time_ms, filled_at, cancelled_at, block_id, has_any_execution)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
