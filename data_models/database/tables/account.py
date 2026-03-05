"""
Account Management Models for managing exchange accounts across multiple bots
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates

from data_models.database.tables.base import Base
from data_models.models.enums.exchange import ExchangeName


class AccountType(PyEnum):
    """Account type enumeration"""

    SPOT = "spot"
    FUTURES = "futures"


class Account(Base):  # type: ignore[misc,no-any-unimported]
    """Model for exchange account configurations"""

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    exchange = Column(String(250), nullable=False)
    account_type = Column(String(20), nullable=False)
    credential_ref = Column(String(200), nullable=False, default="ENCRYPTED")
    is_testnet = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bot_accounts = relationship("BotAccount", back_populates="account", cascade="all, delete-orphan")

    @validates("exchange")
    def validate_exchange(self, key: str, value: str) -> str:
        """Validate exchange name against ExchangeName enum"""
        normalized = value.lower().strip()

        # Get valid exchange base names from ExchangeName enum
        # Map enum values to their base names for validation
        valid_exchanges = {
            "hyperliquid": ExchangeName.HYPERLIQUID,
            "hyperliquid_spot": ExchangeName.HYPERLIQUID_SPOT,
            "bybit": ExchangeName.BYBIT,
            "binance": ExchangeName.BINANCE_FUTURES,  # Base binance maps to futures
            "binance_spot": ExchangeName.BINANCE_SPOT,
            "binance_futures": ExchangeName.BINANCE_FUTURES,
            "ripio_trade": ExchangeName.RIPIO_TRADE,
            "ripio": ExchangeName.RIPIO_TRADE,
            "lighter": ExchangeName.LIGHTER,
            "lighter_spot": ExchangeName.LIGHTER_SPOT,
        }

        if normalized not in valid_exchanges:
            raise ValueError(f"Invalid exchange: {value}. Must be one of {list(valid_exchanges.keys())}")

        return valid_exchanges[normalized].value

    @validates("account_type")
    def validate_account_type(self, key: str, value: str) -> str:
        """Validate account type"""
        try:
            AccountType(value.lower())
            return value.lower()
        except ValueError:
            valid_types = [t.value for t in AccountType]
            raise ValueError(f"Invalid account type: {value}. Must be one of {valid_types}") from None

    @validates("credential_ref")
    def validate_credential_ref(self, key: str, value: str) -> str:
        """Validate credential reference - always returns ENCRYPTED"""
        return "ENCRYPTED"

    def to_dict(self) -> Dict[str, Any]:
        """Convert account to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "exchange": self.exchange,
            "account_type": self.account_type,
            "credential_ref": self.credential_ref,
            "is_testnet": self.is_testnet,
            "is_active": self.is_active,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "bot_count": len(self.bot_accounts) if self.bot_accounts else 0,
        }


class BotAccountRole(PyEnum):
    """Bot account role enumeration"""

    MAKER = "maker"
    TAKER = "taker"


class BotAccount(Base):  # type: ignore[misc,no-any-unimported]
    """Model for bot-account relationships"""

    __tablename__ = "bot_accounts"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Ensure each account can only be assigned once per bot
    # This allows the same account to be used by multiple bots in any role
    __table_args__ = (UniqueConstraint("bot_id", "account_id", name="bot_account_assignment_unique"),)

    # Relationships
    bot = relationship("Bot", back_populates="bot_accounts")
    account = relationship("Account", back_populates="bot_accounts")

    @validates("role")
    def validate_role(self, key: str, value: str) -> str:
        """Validate role — accepts maker/taker (cross-arb) or exchange names (graph bots)"""
        normalized = value.lower().strip()
        valid = {r.value for r in BotAccountRole} | {e.value for e in ExchangeName}
        if normalized not in valid:
            raise ValueError(f"Invalid role: {value}. Must be one of {sorted(valid)}")
        return normalized

    def to_dict(self) -> Dict[str, Any]:
        """Convert bot account to dictionary"""
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "account_id": self.account_id,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "account": self.account.to_dict() if self.account else None,
        }
