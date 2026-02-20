"""Protocol definitions for exchange-related interfaces.

This module contains Protocol classes that define the expected behavior of
exchange components like latency tracking.

Note: BotStateManagerProtocol has been removed. Use ExecutionContext + StateHolder instead.
"""

from enum import Enum
from typing import Optional, Protocol


class AsyncOrderErrorType(Enum):
    """
    DEPRECATED: Error type classification for async order failures.

    This enum is being phased out in favor of OperationResult, which provides
    a cleaner abstraction for engine decision making:

    - Engine should see: OperationResult (SUCCESS, PENDING, TIMEOUT, RETRYABLE, CRITICAL)
    - Broker normalizes these error types to OperationResult internally
    - Engine no longer needs to know about NONCE, RATE_LIMIT, etc.

    Migration Guide:
        Old: Check AsyncOrderErrorType.NONCE → retry with resync
        New: Broker handles nonce retry internally → engine sees RETRYABLE or SUCCESS

        Old: Check AsyncOrderErrorType.RATE_LIMIT → set backoff
        New: Broker sets backoff → engine sees RETRYABLE with should_wait=True

    This enum is kept for backward compatibility during the transition period.
    New code should use OperationResult from data_models.models.enums.trading.
    """

    RATE_LIMIT = "rate_limit"  # 429 errors - needs 60s backoff
    NETWORK = "network"  # Transient network errors - can retry immediately
    INSUFFICIENT_FUNDS = "insufficient_funds"  # Balance issue - needs resolution
    POST_ONLY_REJECTED = "post_only_rejected"  # Order would have crossed - retry ok
    LIMIT_MAKER_REJECTED = "limit_maker_rejected"  # Same as post_only
    WEBSOCKET_NOT_CONNECTED = "websocket_not_connected"  # Connection issue
    NONCE = "nonce"  # Invalid nonce (blockchain exchanges) - resync and retry
    TIMEOUT_NEEDS_RESOLUTION = "timeout_needs_resolution"  # Order sent but confirmation lost - needs REST check
    OTHER = "other"  # Unknown errors - safe default behavior


class LatencyDataProtocol(Protocol):
    """Protocol for latency data tracking.

    This protocol defines the expected behavior of a latency data tracker,
    which is responsible for recording timestamps of various events.
    """

    order_sent_timestamp: Optional[int]
    """Timestamp when order was sent (milliseconds)"""

    def record_order_sent_timestamp(self) -> int:
        """Record when order is sent.

        Returns:
            int: Timestamp in milliseconds
        """
        ...

    def record_cancel_sent_timestamp(self) -> int:
        """Record when cancellation is sent.

        Returns:
            int: Timestamp in milliseconds
        """
        ...


# BotStateManagerProtocol has been REMOVED.
# Use ExecutionContext + StateHolder instead.
# See: src/bot_core/engine/core/context.py
# See: src/bot_core/engine/core/state_holder.py
