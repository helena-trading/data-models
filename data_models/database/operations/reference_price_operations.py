"""Database operations for reference prices."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from data_models.database.core.db_config import get_db_manager
from data_models.database.tables.reference_price import ReferencePrice


class ReferencePriceOperations:
    """Handles database operations for reference prices."""

    def __init__(self) -> None:
        """Initialize reference price operations."""
        self.db = get_db_manager()

    def upsert_reference_price(
        self,
        session: Session,
        exchange: str,
        contract: str,
        price: float,
        timestamp: Optional[datetime] = None,
    ) -> ReferencePrice:
        """Insert or update a reference price for a contract.

        Uses PostgreSQL's ON CONFLICT clause to update if the (exchange, contract)
        combination already exists, otherwise inserts a new record.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name (e.g., 'binance_spot', 'bybit')
            contract: Contract symbol (e.g., 'BTC_USDT')
            price: Mid-price from orderbook
            timestamp: Timestamp for price snapshot (defaults to now)

        Returns:
            Upserted ReferencePrice instance (note: id may not be populated for updates)
        """
        ref_price = ReferencePrice.from_mid_price(exchange=exchange, contract=contract, mid_price=price, timestamp=timestamp)

        query, params = ref_price.to_upsert_query()
        session.execute(text(query), params)
        session.flush()

        # Retrieve the actual record to get the id
        result = (
            session.query(ReferencePrice)
            .filter(ReferencePrice.exchange == exchange, ReferencePrice.contract == contract)
            .one()
        )

        return result

    def upsert_reference_prices_batch(self, session: Session, reference_prices: List[Dict[str, Any]]) -> int:
        """Insert or update multiple reference prices in batch.

        Args:
            session: SQLAlchemy session
            reference_prices: List of dicts with keys: exchange, contract, price, timestamp (optional)

        Returns:
            Number of prices upserted
        """
        if not reference_prices:
            return 0

        # Build batch upsert query
        query = ReferencePrice.batch_upsert_query()
        now = datetime.utcnow()

        # Prepare batch parameters
        params = [
            (
                rp["exchange"],
                rp["contract"],
                rp["price"],
                rp.get("timestamp", now),
                now,  # created_at
                now,  # updated_at
            )
            for rp in reference_prices
        ]

        # Execute batch upsert using executemany
        session.execute(text(query), params)  # type: ignore[arg-type]
        session.flush()

        return len(reference_prices)

    def get_latest_reference_prices(
        self,
        session: Session,
        exchange: Optional[str] = None,
        contract: Optional[str] = None,
    ) -> List[ReferencePrice]:
        """Get latest reference prices with optional filters.

        Args:
            session: SQLAlchemy session
            exchange: Filter by exchange name (optional)
            contract: Filter by contract symbol (optional)

        Returns:
            List of ReferencePrice records matching filters
        """
        query = session.query(ReferencePrice)

        if exchange:
            query = query.filter(ReferencePrice.exchange == exchange)
        if contract:
            query = query.filter(ReferencePrice.contract == contract)

        return query.all()

    def get_all_latest_reference_prices(self, session: Session) -> List[ReferencePrice]:
        """Get all latest reference prices across all exchanges.

        Returns:
            List of all ReferencePrice records
        """
        return session.query(ReferencePrice).all()

    def get_reference_price(self, session: Session, exchange: str, contract: str) -> Optional[ReferencePrice]:
        """Get reference price for a specific exchange and contract.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name
            contract: Contract symbol

        Returns:
            ReferencePrice if found, None otherwise
        """
        return (
            session.query(ReferencePrice)
            .filter(ReferencePrice.exchange == exchange, ReferencePrice.contract == contract)
            .first()
        )

    def get_prices_by_exchange(self, session: Session, exchange: str) -> List[ReferencePrice]:
        """Get all reference prices for a specific exchange.

        Args:
            session: SQLAlchemy session
            exchange: Exchange name to filter by

        Returns:
            List of ReferencePrice records for the exchange
        """
        return session.query(ReferencePrice).filter(ReferencePrice.exchange == exchange).all()

    def get_price_value(self, session: Session, exchange: str, contract: str) -> Optional[float]:
        """Get just the price value for a contract (convenience method).

        Args:
            session: SQLAlchemy session
            exchange: Exchange name
            contract: Contract symbol

        Returns:
            Price as float if found, None otherwise
        """
        ref_price = self.get_reference_price(session, exchange, contract)
        return float(ref_price.price) if ref_price and ref_price.price else None

    def get_prices_as_dict(self, session: Session, exchange: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """Get reference prices as nested dict for easy lookup.

        Returns prices in format:
        {
            "binance_spot": {
                "BTC_USDT": 95432.50,
                "ETH_USDT": 3421.30
            },
            "bybit": {
                "BTC_USDT": 95430.00
            }
        }

        Args:
            session: SQLAlchemy session
            exchange: Filter by exchange (optional)

        Returns:
            Nested dictionary of exchange -> contract -> price
        """
        prices = self.get_latest_reference_prices(session, exchange=exchange)

        result: Dict[str, Dict[str, float]] = {}
        for ref_price in prices:
            exchange_str = str(ref_price.exchange)
            contract_str = str(ref_price.contract)
            if exchange_str not in result:
                result[exchange_str] = {}
            result[exchange_str][contract_str] = float(ref_price.price)

        return result

    def delete_old_prices(
        self,
        session: Session,
        days_to_keep: int = 7,
    ) -> int:
        """Delete old reference prices (keeps only latest per exchange-contract).

        Since reference_prices has a unique constraint on (exchange, contract),
        there should only be one record per pair. This method is provided for
        consistency but typically won't delete anything.

        Args:
            session: SQLAlchemy session
            days_to_keep: Number of days of history to keep (default: 7)

        Returns:
            Number of records deleted
        """
        cutoff_time = datetime.utcnow() - __import__("datetime").timedelta(days=days_to_keep)

        result = session.query(ReferencePrice).filter(ReferencePrice.timestamp < cutoff_time).delete(synchronize_session=False)

        session.flush()
        return result
