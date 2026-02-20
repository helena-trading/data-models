"""Position snapshot database model."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String

from data_models.database.tables.base import Base
from data_models.database.types.persistence_protocols import PositionLike


class PositionSnapshot(Base):  # type: ignore[misc,no-any-unimported]
    """SQLAlchemy model for position snapshots.

    Note: This model is stored in the ANALYTICS database.
    account_id is stored as plain integer (no FK) for cross-database reference
    to the accounts table in the credentials database.
    """

    __tablename__ = "position_snapshots"

    id = Column(Integer, primary_key=True)
    # account_id as plain integer - cross-DB reference to credentials DB accounts table
    # No FK constraint due to dual-database architecture
    account_id = Column(Integer, nullable=True, index=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    exchange = Column(String(250), nullable=False, index=True)
    contract = Column(String(50), nullable=False, index=True)
    position_size = Column(Numeric(30, 10), nullable=True)
    mark_price = Column(Numeric(30, 10), nullable=True)
    notional_value = Column(Numeric(30, 10), nullable=True)
    unrealized_pnl = Column(Numeric(30, 10), nullable=True)
    margin_used = Column(Numeric(30, 10), nullable=True)
    entry_price = Column(Numeric(30, 10), nullable=True)
    liquidation_price = Column(Numeric(30, 10), nullable=True)
    # correlation_confidence tracks backfill quality: NEW, HIGH, MEDIUM, LOW, AMBIGUOUS, UNPROCESSED
    correlation_confidence = Column(String(20), nullable=True, default="NEW")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_position_snapshots_exchange_contract", "exchange", "contract"),
        Index("idx_position_snapshots_time", "time"),
        Index("idx_position_snapshots_exchange_time", "exchange", "time"),
        Index("idx_position_snapshots_account_exchange_time", "account_id", "exchange", "time"),
    )

    @classmethod
    def from_position(
        cls,
        position: PositionLike,
        exchange: str,
        time: Optional[datetime] = None,
        account_id: Optional[int] = None,
    ) -> "PositionSnapshot":
        """Create PositionSnapshot from Position model.

        Args:
            position: Position model from exchange gateway
            exchange: Exchange name
            time: Timestamp for position snapshot (defaults to now)
            account_id: Account ID for cross-database reference (optional)

        Returns:
            PositionSnapshot instance
        """
        return cls.from_values(
            exchange=exchange,
            contract=position.contract,
            position_size=position.size,
            mark_price=position.mark_price,
            notional_value=position.notional_value,
            unrealized_pnl=position.unrealized_pnl,
            entry_price=position.entry_price,
            liquidation_price=position.liquidation_price,
            time=time,
            account_id=account_id,
        )

    @classmethod
    def from_values(
        cls,
        exchange: str,
        contract: str,
        position_size: Optional[float],
        mark_price: Optional[float] = None,
        notional_value: Optional[float] = None,
        unrealized_pnl: Optional[float] = None,
        entry_price: Optional[float] = None,
        liquidation_price: Optional[float] = None,
        time: Optional[datetime] = None,
        account_id: Optional[int] = None,
    ) -> "PositionSnapshot":
        """Create PositionSnapshot directly from persistence values."""
        return cls(
            account_id=account_id,
            time=time or datetime.utcnow(),
            exchange=exchange,
            contract=contract,
            position_size=Decimal(str(position_size)) if position_size is not None else None,
            mark_price=Decimal(str(mark_price)) if mark_price is not None else None,
            notional_value=(Decimal(str(notional_value)) if notional_value is not None else None),
            unrealized_pnl=Decimal(str(unrealized_pnl)) if unrealized_pnl is not None else None,
            margin_used=None,  # Position model doesn't have margin field
            entry_price=Decimal(str(entry_price)) if entry_price is not None else None,
            liquidation_price=Decimal(str(liquidation_price)) if liquidation_price is not None else None,
            correlation_confidence="NEW" if account_id else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary for API responses.

        Returns:
            Dictionary representation of position
        """
        return {
            "id": self.id,
            "account_id": self.account_id,
            "time": self.time.isoformat() if self.time else None,
            "exchange": self.exchange,
            "contract": self.contract,
            "position_size": float(self.position_size) if self.position_size is not None else None,
            "mark_price": float(self.mark_price) if self.mark_price is not None else None,
            "notional_value": float(self.notional_value) if self.notional_value is not None else None,
            "unrealized_pnl": float(self.unrealized_pnl) if self.unrealized_pnl is not None else None,
            "margin_used": float(self.margin_used) if self.margin_used is not None else None,
            "entry_price": float(self.entry_price) if self.entry_price is not None else None,
            "liquidation_price": float(self.liquidation_price) if self.liquidation_price is not None else None,
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
            INSERT INTO position_snapshots
            (account_id, time, exchange, contract, position_size, mark_price,
             notional_value, unrealized_pnl, margin_used, entry_price, liquidation_price, correlation_confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.account_id,
            self.time,
            self.exchange,
            self.contract,
            self.position_size,
            self.mark_price,
            self.notional_value,
            self.unrealized_pnl,
            self.margin_used,
            self.entry_price,
            self.liquidation_price,
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
            INSERT INTO position_snapshots
            (account_id, time, exchange, contract, position_size, mark_price,
             notional_value, unrealized_pnl, margin_used, entry_price, liquidation_price, correlation_confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
