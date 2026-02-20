"""Block trade database model."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Tuple

from data_models.models.reporting.report_models import BlockTradeInfo


@dataclass
class BlockTrade:
    """Block trade record for database storage."""

    time: datetime
    block_id: uuid.UUID
    client_id: Optional[str] = None
    maker_order_id: Optional[int] = None
    taker_order_id: Optional[int] = None
    maker_exchange: Optional[str] = None
    taker_exchange: Optional[str] = None
    contract: Optional[str] = None
    size: Optional[Decimal] = None
    maker_price: Optional[Decimal] = None
    taker_price: Optional[Decimal] = None
    spread_captured: Optional[Decimal] = None
    total_fees: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    lifecycle_state: Optional[str] = None
    execution_time_ms: Optional[int] = None
    route: Optional[str] = None
    bot_id: Optional[int] = None
    run_id: Optional[int] = None
    # New fields for proper buy/sell tracking
    buy_exchange: Optional[str] = None
    sell_exchange: Optional[str] = None
    buy_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    order_type: Optional[str] = None
    slippage_pct: Optional[Decimal] = None
    attempts: Optional[int] = None
    # New fields for slippage tracking
    expected_spread: Optional[Decimal] = None
    slippage_bps: Optional[Decimal] = None
    maker_fee: Optional[Decimal] = None
    taker_fee: Optional[Decimal] = None
    # Internal IDs for reliable joins with order_executions
    # These are the canonical identifiers - always available, unlike exchange_order_ids
    maker_internal_id: Optional[str] = None
    taker_internal_id: Optional[str] = None

    @classmethod
    def from_block_trade_info(
        cls, info: BlockTradeInfo, bot_id: Optional[int] = None, run_id: Optional[int] = None
    ) -> "BlockTrade":
        """Create from BlockTradeInfo model.

        Args:
            info: BlockTradeInfo containing trade details
            bot_id: Optional bot ID for tracking which bot executed the trade
            run_id: Optional run ID for tracking which bot run session executed the trade
        """
        # Calculate spread captured based on price difference
        spread_captured = None
        if info.price_difference and info.buy_size:
            spread_captured = Decimal(str(info.price_difference * info.buy_size))
        elif info.executed_spread and info.trade_value:
            spread_captured = Decimal(str(info.executed_spread * info.trade_value / 100))

        # Calculate total fees from trade info if available
        total_fees = Decimal("0")
        if info.buy_side_trade and info.buy_side_trade.fees:
            total_fees += Decimal(str(info.buy_side_trade.fees))
        if info.sell_side_trade and info.sell_side_trade.fees:
            total_fees += Decimal(str(info.sell_side_trade.fees))

        # Calculate net profit
        net_profit = None
        if spread_captured is not None:
            net_profit = spread_captured - total_fees

        # Get order IDs from trades if available
        maker_order_id = None
        taker_order_id = None
        maker_internal_id = None
        taker_internal_id = None
        contract = None

        # Use maker_exchange and taker_exchange if available
        # Fallback to buy/sell is INCORRECT but kept for backward compatibility with old data
        # WARNING: maker != buy and taker != sell - they are orthogonal concepts!
        # The correct values should be set in BlockTradeInfo by the caller
        maker_exchange = info.maker_exchange or info.buy_exchange
        taker_exchange = info.taker_exchange or info.sell_exchange

        # Determine which trade corresponds to maker and taker based on exchange
        if info.buy_side_trade and info.sell_side_trade:
            if info.buy_side_trade.exchange == maker_exchange:
                # Buy side is maker
                maker_order_id = (
                    int(info.buy_side_trade.order_id)
                    if info.buy_side_trade.order_id and str(info.buy_side_trade.order_id).strip().isdigit()
                    else None
                )
                taker_order_id = (
                    int(info.sell_side_trade.order_id)
                    if info.sell_side_trade.order_id and str(info.sell_side_trade.order_id).strip().isdigit()
                    else None
                )
                # Internal IDs - the canonical identifiers for reliable joins
                maker_internal_id = info.buy_side_trade.internal_id if info.buy_side_trade.internal_id else None
                taker_internal_id = info.sell_side_trade.internal_id if info.sell_side_trade.internal_id else None
            else:
                # Sell side is maker
                maker_order_id = (
                    int(info.sell_side_trade.order_id)
                    if info.sell_side_trade.order_id and str(info.sell_side_trade.order_id).strip().isdigit()
                    else None
                )
                taker_order_id = (
                    int(info.buy_side_trade.order_id)
                    if info.buy_side_trade.order_id and str(info.buy_side_trade.order_id).strip().isdigit()
                    else None
                )
                # Internal IDs - the canonical identifiers for reliable joins
                maker_internal_id = info.sell_side_trade.internal_id if info.sell_side_trade.internal_id else None
                taker_internal_id = info.buy_side_trade.internal_id if info.buy_side_trade.internal_id else None

            # Get contract from either trade
            contract = info.buy_side_trade.contract or info.sell_side_trade.contract

        # Convert lifecycle state to string
        lifecycle_state_map = {0: "pending", 1: "active", 2: "completed", 3: "failed"}
        lifecycle_state = lifecycle_state_map.get(info.lifecycle_state, "unknown")

        return cls(
            time=datetime.now(),  # Use current time since BlockTradeInfo uses string timestamp
            block_id=uuid.uuid4(),  # Generate new UUID for database
            client_id=info.client_id_id,  # Note: field is client_id_id in BlockTradeInfo
            maker_order_id=maker_order_id,
            taker_order_id=taker_order_id,
            maker_exchange=maker_exchange,  # Use the determined maker exchange
            taker_exchange=taker_exchange,  # Use the determined taker exchange
            contract=contract,
            size=Decimal(str(info.buy_size)) if info.buy_size else None,
            # Set prices based on which trade is maker vs taker
            maker_price=(
                Decimal(
                    str(
                        info.buy_price
                        if info.buy_side_trade and info.buy_side_trade.exchange == maker_exchange
                        else info.sell_price
                    )
                )
                if (info.buy_price or info.sell_price)
                else None
            ),
            taker_price=(
                Decimal(
                    str(
                        info.sell_price
                        if info.sell_side_trade and info.sell_side_trade.exchange == taker_exchange
                        else info.buy_price
                    )
                )
                if (info.buy_price or info.sell_price)
                else None
            ),
            spread_captured=spread_captured,
            total_fees=total_fees,
            net_profit=net_profit,
            lifecycle_state=lifecycle_state,
            execution_time_ms=info.latency,  # Use latency as execution time
            route=info.route or None,
            bot_id=bot_id,  # Use the provided bot_id parameter
            run_id=run_id,  # Use the provided run_id parameter
            # New fields for buy/sell tracking
            buy_exchange=info.buy_exchange,
            sell_exchange=info.sell_exchange,
            buy_price=Decimal(str(info.buy_price)) if info.buy_price else None,
            sell_price=Decimal(str(info.sell_price)) if info.sell_price else None,
            order_type=info.maker_type if info.maker_type else None,
            slippage_pct=Decimal(str(info.slippage)) if info.slippage else None,
            attempts=info.tries,  # BlockTradeInfo.tries has default=0
            # New slippage tracking fields
            # Use 'is not None' to preserve 0.0 values (0.0 is falsy in Python)
            expected_spread=Decimal(str(info.expected_spread)) if info.expected_spread is not None else None,
            slippage_bps=Decimal(str(info.slippage_bps)) if info.slippage_bps is not None else None,
            maker_fee=Decimal(str(info.maker_fee)) if info.maker_fee is not None else None,
            taker_fee=Decimal(str(info.taker_fee)) if info.taker_fee is not None else None,
            # Internal IDs for reliable joins with order_executions
            maker_internal_id=maker_internal_id,
            taker_internal_id=taker_internal_id,
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters."""
        query = """
            INSERT INTO block_trades
            (time, block_id, client_id, maker_order_id, taker_order_id,
             maker_exchange, taker_exchange, contract, size,
             maker_price, taker_price, spread_captured, total_fees,
             net_profit, lifecycle_state, execution_time_ms, route, bot_id, run_id,
             buy_exchange, sell_exchange, buy_price, sell_price,
             order_type, slippage_pct, attempts,
             expected_spread, slippage_bps, maker_fee, taker_fee,
             maker_internal_id, taker_internal_id)
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        params = (
            self.time,
            str(self.block_id),  # Convert UUID to string
            self.client_id,
            self.maker_order_id,
            self.taker_order_id,
            self.maker_exchange,
            self.taker_exchange,
            self.contract,
            self.size,
            self.maker_price,
            self.taker_price,
            self.spread_captured,
            self.total_fees,
            self.net_profit,
            self.lifecycle_state,
            self.execution_time_ms,
            self.route,
            self.bot_id,
            self.run_id,
            self.buy_exchange,
            self.sell_exchange,
            self.buy_price,
            self.sell_price,
            self.order_type,
            self.slippage_pct,
            self.attempts,
            self.expected_spread,
            self.slippage_bps,
            self.maker_fee,
            self.taker_fee,
            self.maker_internal_id,
            self.taker_internal_id,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts."""
        return """
            INSERT INTO block_trades
            (time, block_id, client_id, maker_order_id, taker_order_id,
             maker_exchange, taker_exchange, contract, size,
             maker_price, taker_price, spread_captured, total_fees,
             net_profit, lifecycle_state, execution_time_ms, route, bot_id, run_id,
             buy_exchange, sell_exchange, buy_price, sell_price,
             order_type, slippage_pct, attempts,
             expected_spread, slippage_bps, maker_fee, taker_fee,
             maker_internal_id, taker_internal_id)
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
