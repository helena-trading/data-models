"""Reference price database model."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Tuple

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String, UniqueConstraint

from data_models.database.tables.base import Base


class ReferencePrice(Base):  # type: ignore[misc,no-any-unimported]
    """SQLAlchemy model for reference price snapshots.

    Stores the latest market mid-price for each contract on each exchange.
    Used by dashboard for crypto-to-value conversions.
    """

    __tablename__ = "reference_prices"

    id = Column(Integer, primary_key=True)
    exchange = Column(String(250), nullable=False, index=True)
    contract = Column(String(50), nullable=False, index=True)
    price = Column(Numeric(30, 10), nullable=False)  # Mid-price from orderbook
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes and constraints for efficient queries and upserts
    __table_args__ = (
        # Unique constraint for latest price lookups and upserts
        UniqueConstraint("exchange", "contract", name="uq_reference_price_exchange_contract"),
        # Index for time-based queries
        Index("idx_reference_prices_exchange_contract", "exchange", "contract"),
        Index("idx_reference_prices_timestamp", "timestamp"),
    )

    @classmethod
    def from_orderbook(
        cls,
        exchange: str,
        contract: str,
        best_bid: float,
        best_ask: float,
        timestamp: Optional[datetime] = None,
    ) -> "ReferencePrice":
        """Create ReferencePrice from orderbook data.

        Args:
            exchange: Exchange name (e.g., 'binance_spot', 'bybit')
            contract: Contract symbol (e.g., 'BTC_USDT')
            best_bid: Best bid price from orderbook
            best_ask: Best ask price from orderbook
            timestamp: Timestamp for price snapshot (defaults to now)

        Returns:
            ReferencePrice instance with mid-price calculated from bid/ask
        """
        # Calculate mid-price
        mid_price = (best_bid + best_ask) / 2
        mid_price_decimal = Decimal(str(mid_price))

        return cls(
            exchange=exchange,
            contract=contract,
            price=mid_price_decimal,
            timestamp=timestamp or datetime.utcnow(),
        )

    @classmethod
    def from_mid_price(
        cls,
        exchange: str,
        contract: str,
        mid_price: float,
        timestamp: Optional[datetime] = None,
    ) -> "ReferencePrice":
        """Create ReferencePrice from pre-calculated mid-price.

        Args:
            exchange: Exchange name
            contract: Contract symbol
            mid_price: Pre-calculated mid-price
            timestamp: Timestamp for price snapshot (defaults to now)

        Returns:
            ReferencePrice instance
        """
        return cls(
            exchange=exchange,
            contract=contract,
            price=Decimal(str(mid_price)),
            timestamp=timestamp or datetime.utcnow(),
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters (DatabaseWriter compatibility).

        Returns:
            Tuple of (query, params) for raw SQL insert
        """
        query = """
            INSERT INTO reference_prices
            (exchange, contract, price, timestamp)
            VALUES (%s, %s, %s, %s)
        """

        params = (
            self.exchange,
            self.contract,
            self.price,
            self.timestamp,
        )

        return query, params

    def to_upsert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate upsert query and parameters for latest price updates.

        Uses PostgreSQL's ON CONFLICT clause to update if exists, insert if not.

        Returns:
            Tuple of (query, params) for raw SQL upsert
        """
        query = """
            INSERT INTO reference_prices
            (exchange, contract, price, timestamp, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (exchange, contract)
            DO UPDATE SET
                price = EXCLUDED.price,
                timestamp = EXCLUDED.timestamp,
                updated_at = EXCLUDED.updated_at
        """

        now = datetime.utcnow()
        params = (
            self.exchange,
            self.contract,
            self.price,
            self.timestamp,
            now,  # created_at (only used on insert)
            now,  # updated_at (always updated)
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get SQL query for batch inserts (DatabaseWriter compatibility).

        Returns:
            Raw SQL INSERT query for batch operations
        """
        return """
            INSERT INTO reference_prices
            (exchange, contract, price, timestamp)
            VALUES (%s, %s, %s, %s)
        """

    @staticmethod
    def batch_upsert_query() -> str:
        """Get SQL query for batch upserts (latest price updates).

        Returns:
            Raw SQL INSERT...ON CONFLICT query for batch operations
        """
        return """
            INSERT INTO reference_prices
            (exchange, contract, price, timestamp, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (exchange, contract)
            DO UPDATE SET
                price = EXCLUDED.price,
                timestamp = EXCLUDED.timestamp,
                updated_at = EXCLUDED.updated_at
        """
