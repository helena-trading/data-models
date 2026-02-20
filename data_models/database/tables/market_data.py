"""Market data database model."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Tuple

from data_models.database.types.persistence_protocols import OrderbookLike


@dataclass
class MarketData:
    """Market data record for database storage."""

    time: datetime
    exchange: str
    contract: str
    bid_price: Optional[Decimal] = None
    bid_size: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    ask_size: Optional[Decimal] = None
    spread_bps: Optional[Decimal] = None
    mid_price: Optional[Decimal] = None
    last_update_id: Optional[int] = None

    @classmethod
    def from_orderbook(cls, orderbook: OrderbookLike, exchange: str) -> "MarketData":
        """Create from Orderbook model."""
        bid_price = None
        bid_size = None
        ask_price = None
        ask_size = None

        # Get best bid/ask
        if orderbook.bids and len(orderbook.bids) > 0:
            bid_price = Decimal(str(orderbook.bids[0].price))
            bid_size = Decimal(str(orderbook.bids[0].amount))  # Changed from volume to amount

        if orderbook.asks and len(orderbook.asks) > 0:
            ask_price = Decimal(str(orderbook.asks[0].price))
            ask_size = Decimal(str(orderbook.asks[0].amount))  # Changed from volume to amount

        # Calculate spread and mid price
        spread_bps = None
        mid_price = None
        if bid_price and ask_price:
            spread = ask_price - bid_price
            mid_price = (bid_price + ask_price) / 2
            if mid_price is not None and mid_price > 0:
                spread_bps = (spread / mid_price) * 10000  # Convert to basis points

        return cls(
            time=(datetime.fromtimestamp(orderbook.timestamp / 1000) if orderbook.timestamp else datetime.now()),
            exchange=exchange,
            contract=orderbook.contract,  # Changed from trading_pair to contract
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
            spread_bps=spread_bps,
            mid_price=mid_price,
            last_update_id=orderbook.sequence_number,  # Changed from last_update_id to sequence_number
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters."""
        query = """
            INSERT INTO market_data
            (time, exchange, contract, bid_price, bid_size,
             ask_price, ask_size, spread_bps, mid_price, last_update_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.time,
            self.exchange,
            self.contract,
            self.bid_price,
            self.bid_size,
            self.ask_price,
            self.ask_size,
            self.spread_bps,
            self.mid_price,
            self.last_update_id,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts."""
        return """
            INSERT INTO market_data
            (time, exchange, contract, bid_price, bid_size,
             ask_price, ask_size, spread_bps, mid_price, last_update_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
