"""Account balance database model."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String

from data_models.database.tables.base import Base
from data_models.database.types.persistence_protocols import BalanceLike


class AccountBalance(Base):  # type: ignore[misc,no-any-unimported]
    """SQLAlchemy model for account balance snapshots.

    Note: This model is stored in the ANALYTICS database.
    account_id is stored as plain integer (no FK) for cross-database reference
    to the accounts table in the credentials database.
    """

    __tablename__ = "account_balances"

    id = Column(Integer, primary_key=True)
    # account_id as plain integer - cross-DB reference to credentials DB accounts table
    # No FK constraint due to dual-database architecture
    account_id = Column(Integer, nullable=True, index=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    exchange = Column(String(250), nullable=False, index=True)
    asset = Column(String(20), nullable=False, index=True)
    balance = Column(Numeric(30, 10), nullable=True)
    usd_value = Column(Numeric(30, 10), nullable=True)
    allocated = Column(Numeric(30, 10), nullable=True)
    available = Column(Numeric(30, 10), nullable=True)
    # correlation_confidence tracks backfill quality: NEW, HIGH, MEDIUM, LOW, AMBIGUOUS, UNPROCESSED
    correlation_confidence = Column(String(20), nullable=True, default="NEW")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_account_balances_exchange_asset", "exchange", "asset"),
        Index("idx_account_balances_time", "time"),
        Index("idx_account_balances_exchange_time", "exchange", "time"),
        Index("idx_account_balances_account_exchange_time", "account_id", "exchange", "time"),
    )

    @classmethod
    def from_balance(
        cls,
        balance: BalanceLike,
        exchange: str,
        usd_value: Optional[float] = None,
        time: Optional[datetime] = None,
        account_id: Optional[int] = None,
    ) -> "AccountBalance":
        """Create AccountBalance from Balance model.

        Args:
            balance: Balance model from exchange gateway
            exchange: Exchange name
            usd_value: USD value of balance (optional)
            time: Timestamp for balance snapshot (defaults to now)
            account_id: Account ID for cross-database reference (optional)

        Returns:
            AccountBalance instance
        """
        return cls.from_values(
            exchange=exchange,
            asset=balance.currency,
            balance=balance.total,
            usd_value=usd_value,
            allocated=balance.locked,
            available=balance.free,
            time=time,
            account_id=account_id,
        )

    @classmethod
    def from_values(
        cls,
        exchange: str,
        asset: str,
        balance: Optional[float],
        usd_value: Optional[float] = None,
        allocated: Optional[float] = None,
        available: Optional[float] = None,
        time: Optional[datetime] = None,
        account_id: Optional[int] = None,
    ) -> "AccountBalance":
        """Create AccountBalance directly from persistence values."""
        return cls(
            account_id=account_id,
            time=time or datetime.utcnow(),
            exchange=exchange,
            asset=asset,
            balance=Decimal(str(balance)) if balance is not None else None,
            usd_value=Decimal(str(usd_value)) if usd_value else None,
            allocated=Decimal(str(allocated)) if allocated is not None else Decimal("0"),
            available=Decimal(str(available)) if available is not None else Decimal("0"),
            correlation_confidence="NEW" if account_id else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert balance to dictionary for API responses.

        Returns:
            Dictionary representation of balance
        """
        return {
            "id": self.id,
            "account_id": self.account_id,
            "time": self.time.isoformat() if self.time else None,
            "exchange": self.exchange,
            "asset": self.asset,
            "balance": float(self.balance) if self.balance is not None else None,
            "usd_value": float(self.usd_value) if self.usd_value is not None else None,
            "allocated": float(self.allocated) if self.allocated is not None else None,
            "available": float(self.available) if self.available is not None else None,
            "correlation_confidence": self.correlation_confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters (DatabaseWriter compatibility).

        Returns:
            Tuple of (query, params) for raw SQL insert
        """
        query = """
            INSERT INTO account_balances
            (account_id, time, exchange, asset, balance, usd_value, allocated, available, correlation_confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.account_id,
            self.time,
            self.exchange,
            self.asset,
            self.balance,
            self.usd_value,
            self.allocated,
            self.available,
            self.correlation_confidence,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get SQL query for batch inserts (DatabaseWriter compatibility).

        Returns:
            Raw SQL INSERT query for batch operations
        """
        return """
            INSERT INTO account_balances
            (account_id, time, exchange, asset, balance, usd_value, allocated, available, correlation_confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
