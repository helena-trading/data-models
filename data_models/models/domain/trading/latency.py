"""
Latency data model for storing performance metrics during bot trading operations.

This model tracks latency at various stages of the trading cycle to help
monitor and optimize bot performance.
"""

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class LatencyData(BaseModel):
    """
    Model for storing latency-related data during bot operations.

    Tracks timestamps and latency metrics throughout the trading cycle,
    from orderbook retrieval through order execution and cancellation.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    state_timestamps: Dict[str, int] = Field(
        default_factory=dict,
        description="Timestamps for state transitions (state_name -> timestamp in ms)",
    )

    order_sent_timestamp: Optional[int] = Field(
        None,
        ge=0,
        description="Timestamp when order was sent to exchange (milliseconds)",
    )

    order_received_timestamp: Optional[int] = Field(
        None,
        ge=0,
        description="Timestamp when order confirmation was received (milliseconds)",
    )

    cancel_sent_timestamp: Optional[int] = Field(
        None,
        ge=0,
        description="Timestamp when cancellation was sent (milliseconds)",
    )

    cancel_received_timestamp: Optional[int] = Field(
        None,
        ge=0,
        description="Timestamp when cancellation confirmation was received (milliseconds)",
    )

    maker_latency: Optional[int] = Field(
        None,
        ge=0,
        description="Maker order execution latency (milliseconds)",
    )

    taker_latency: Optional[int] = Field(
        None,
        ge=0,
        description="Taker order execution latency (milliseconds)",
    )

    cancel_maker_latency: Optional[int] = Field(
        None,
        ge=0,
        description="Maker order cancellation latency (milliseconds)",
    )

    orderbook_latency_maker: Optional[int] = Field(
        None,
        description="Latency to retrieve maker orderbook (milliseconds, negative indicates clock skew)",
    )

    orderbook_latency_taker: Optional[int] = Field(
        None,
        description="Latency to retrieve taker orderbook (milliseconds, negative indicates clock skew)",
    )

    cycle_latency: Optional[int] = Field(
        None,
        description="Time between maker and taker execution (milliseconds, negative indicates timing anomaly)",
    )

    taker_liquidity: Optional[float] = Field(
        None,
        ge=0.0,
        description="Available liquidity on taker side",
    )

    maker_type: Optional[str] = Field(
        None,
        description="Type of maker order (e.g., 'limit', 'post_only')",
    )

    taker_price: Optional[float] = Field(
        None,
        gt=0.0,
        description="Execution price on taker side",
    )

    client_id: Optional[str] = Field(
        None,
        description="Client order ID for tracking",
    )

    liquidation_location: Optional[int] = Field(
        None,
        ge=0,
        le=3,
        description="Where liquidation occurred: 0=Order creation, 1=Order Status, 2=Order Cancellation, 3=REST Update",
    )

    taker_tries: int = Field(
        default=0,
        ge=0,
        description="Number of taker order attempts",
    )

    # Exchange and contract information
    maker_exchange: Optional[str] = Field(
        None,
        description="Exchange where maker order was placed",
    )

    taker_exchange: Optional[str] = Field(
        None,
        description="Exchange where taker order was placed",
    )

    maker_contract: Optional[str] = Field(
        None,
        description="Contract/symbol for maker order",
    )

    route_id: Optional[int] = Field(
        None,
        ge=0,
        description="Route identifier for this trade",
    )

    timestamp: Optional[int] = Field(
        None,
        ge=0,
        description="Timestamp of the latency data (milliseconds since epoch)",
    )

    # Additional latency metrics
    cancel_request_latency: Optional[int] = Field(
        None,
        ge=0,
        description="Latency from cancel request initiation (milliseconds)",
    )

    cancel_execution_latency: Optional[int] = Field(
        None,
        ge=0,
        description="Latency from cancel execution (milliseconds)",
    )

    # Fill notification latency - critical metric for understanding information delay
    fill_notification_latency_ms: Optional[int] = Field(
        None,
        ge=0,
        description=(
            "Latency from order fill on exchange (statusTimestamp) to WebSocket "
            "notification received. This is the 'blindness window' during which "
            "the order is filled but we don't know it yet."
        ),
    )

    # Bot identification for correlation
    bot_id: Optional[int] = Field(
        None,
        ge=0,
        description="Bot ID that generated this latency data",
    )
