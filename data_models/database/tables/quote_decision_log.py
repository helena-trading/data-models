"""Quote decision log database model.

Logs every quote decision from the SignalProcessor for analysis and ML training.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from psycopg.types.json import Jsonb


@dataclass
class QuoteDecisionLog:
    """
    Quote decision log record for database storage.

    Captures every decision from the SignalProcessor, including:
    - The decision action (QUOTE, QUOTE_WIDE, SKIP)
    - Fill probability estimate
    - Expected value calculation
    - Market features at decision time
    - Fair value context

    This data is used for:
    1. Performance analysis (hit rate, EV realization)
    2. Model calibration (compare P(fill) estimates to actual fills)
    3. ML training data generation

    Attributes:
        time: Decision timestamp
        bot_id: Bot that made the decision
        route_id: Trading route
        contract: Contract symbol (e.g., "BTC_USDT")
        internal_id: Unique ID linking to order lifecycle
        action: Decision action (quote/quote_wide/skip)
        proposed_price: Price the engine proposed
        adjusted_price: Price after signal adjustment (null for skip)
        is_bid: Whether this is a bid (buy) order
        fill_probability: Estimated fill probability (0-1)
        expected_value_bps: Expected value in basis points
        fair_mid: Fair mid price from pricing orchestrator
        fair_bid: Fair bid price
        fair_ask: Fair ask price
        funding_shift_bps: Funding rate adjustment in bps
        confidence: Fair value confidence score (0-1)
        volatility_1m: 1-minute volatility
        volatility_5m: 5-minute volatility
        spread_bps: Current spread in basis points
        imbalance: Orderbook imbalance (-1 to 1)
        depth_bid_usd: Bid depth in USD
        depth_ask_usd: Ask depth in USD
        orderbook_age_ms: Orderbook staleness
        reason: Human-readable decision reason
        features_snapshot: Full features snapshot (JSON)
        decision_time_ns: Time taken for decision in nanoseconds
    """

    time: datetime
    bot_id: int
    route_id: str
    contract: str
    internal_id: str
    action: str  # "quote", "quote_wide", "skip"
    proposed_price: Decimal
    is_bid: bool
    fill_probability: float
    expected_value_bps: float
    fair_mid: Decimal
    fair_bid: Decimal
    fair_ask: Decimal

    # Optional fields
    adjusted_price: Optional[Decimal] = None
    funding_shift_bps: Optional[float] = None
    confidence: Optional[float] = None
    volatility_1m: Optional[float] = None
    volatility_5m: Optional[float] = None
    spread_bps: Optional[float] = None
    imbalance: Optional[float] = None
    depth_bid_usd: Optional[float] = None
    depth_ask_usd: Optional[float] = None
    orderbook_age_ms: Optional[int] = None
    reason: Optional[str] = None
    features_snapshot: Optional[Dict[str, Any]] = field(default_factory=dict)
    decision_time_ns: Optional[int] = None
    wide_spread_adjustment_bps: Optional[float] = None

    @classmethod
    def from_decision(
        cls,
        decision: Any,  # QuoteDecision (future type)
        bot_id: int,
        route_id: str,
        contract: str,
        proposed_price: float,
        is_bid: bool,
        fair_value: Any,  # FairValueContext (future type)
        features: Optional[Any] = None,  # MarketFeatures (future type)
        decision_time_ns: Optional[int] = None,
    ) -> "QuoteDecisionLog":
        """
        Create from QuoteDecision and related context.

        Args:
            decision: QuoteDecision from SignalProcessor
            bot_id: Bot ID
            route_id: Route identifier
            contract: Contract symbol
            proposed_price: Original proposed price
            is_bid: Whether bid order
            fair_value: FairValueContext
            features: Optional MarketFeatures
            decision_time_ns: Time to make decision
        """
        return cls(
            time=datetime.now(tz=timezone.utc),
            bot_id=bot_id,
            route_id=route_id,
            contract=contract,
            internal_id=decision.internal_id or "",
            action=decision.action.value,
            proposed_price=Decimal(str(proposed_price)),
            adjusted_price=(Decimal(str(decision.adjusted_price)) if decision.adjusted_price else None),
            is_bid=is_bid,
            fill_probability=decision.fill_probability,
            expected_value_bps=decision.expected_value,
            fair_mid=Decimal(str(fair_value.fair_mid)),
            fair_bid=Decimal(str(fair_value.fair_bid)),
            fair_ask=Decimal(str(fair_value.fair_ask)),
            funding_shift_bps=fair_value.funding_shift_bps,
            confidence=fair_value.confidence,
            volatility_1m=features.volatility_1m if features else None,
            volatility_5m=features.volatility_5m if features else None,
            spread_bps=features.spread_bps if features else None,
            imbalance=features.imbalance if features else None,
            depth_bid_usd=features.bid_depth_usd if features else None,
            depth_ask_usd=features.ask_depth_usd if features else None,
            orderbook_age_ms=features.orderbook_age_ms if features else None,
            reason=decision.reason,
            features_snapshot=decision.features_snapshot,
            decision_time_ns=decision_time_ns,
            wide_spread_adjustment_bps=decision.wide_spread_adjustment_bps,
        )

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters."""
        query = """
            INSERT INTO quote_decision_logs
            (time, bot_id, route_id, contract, internal_id, action,
             proposed_price, adjusted_price, is_bid, fill_probability,
             expected_value_bps, fair_mid, fair_bid, fair_ask,
             funding_shift_bps, confidence, volatility_1m, volatility_5m,
             spread_bps, imbalance, depth_bid_usd, depth_ask_usd,
             orderbook_age_ms, reason, features_snapshot, decision_time_ns,
             wide_spread_adjustment_bps)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.time,
            self.bot_id,
            self.route_id,
            self.contract,
            self.internal_id,
            self.action,
            self.proposed_price,
            self.adjusted_price,
            self.is_bid,
            self.fill_probability,
            self.expected_value_bps,
            self.fair_mid,
            self.fair_bid,
            self.fair_ask,
            self.funding_shift_bps,
            self.confidence,
            self.volatility_1m,
            self.volatility_5m,
            self.spread_bps,
            self.imbalance,
            self.depth_bid_usd,
            self.depth_ask_usd,
            self.orderbook_age_ms,
            self.reason,
            Jsonb(self.features_snapshot) if self.features_snapshot else None,
            self.decision_time_ns,
            self.wide_spread_adjustment_bps,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts."""
        return """
            INSERT INTO quote_decision_logs
            (time, bot_id, route_id, contract, internal_id, action,
             proposed_price, adjusted_price, is_bid, fill_probability,
             expected_value_bps, fair_mid, fair_bid, fair_ask,
             funding_shift_bps, confidence, volatility_1m, volatility_5m,
             spread_bps, imbalance, depth_bid_usd, depth_ask_usd,
             orderbook_age_ms, reason, features_snapshot, decision_time_ns,
             wide_spread_adjustment_bps)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    def to_params(self) -> Tuple[Any, ...]:
        """Get parameters for batch insert."""
        return (
            self.time,
            self.bot_id,
            self.route_id,
            self.contract,
            self.internal_id,
            self.action,
            self.proposed_price,
            self.adjusted_price,
            self.is_bid,
            self.fill_probability,
            self.expected_value_bps,
            self.fair_mid,
            self.fair_bid,
            self.fair_ask,
            self.funding_shift_bps,
            self.confidence,
            self.volatility_1m,
            self.volatility_5m,
            self.spread_bps,
            self.imbalance,
            self.depth_bid_usd,
            self.depth_ask_usd,
            self.orderbook_age_ms,
            self.reason,
            Jsonb(self.features_snapshot) if self.features_snapshot else None,
            self.decision_time_ns,
            self.wide_spread_adjustment_bps,
        )
