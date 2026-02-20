"""Latency metrics database model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from psycopg.types.json import Jsonb

from data_models.database.types.persistence_protocols import LatencyDataLike


@dataclass
class LatencyMetric:
    """Latency metric record for database storage.

    Metric Types:
    - 'maker_orderbook_fetch': Time to fetch orderbook from maker exchange
    - 'maker_order_ack': Time from sending maker order to exchange acknowledgment
    - 'cancel_request_send': Time from cancel initiation to cancel request sent
    - 'trade_cycle': Total time from maker fill to taker fill completion
    - 'maker_fill_ws_delay': Time from exchange fill to WebSocket notification (blindness window)
    """

    time: datetime
    metric_type: str
    exchange_maker: Optional[str] = None
    exchange_taker: Optional[str] = None
    contract: Optional[str] = None
    latency_ms: Optional[int] = None
    state_transitions: Optional[Dict[str, Any]] = field(default_factory=dict)
    route_id: Optional[int] = None
    bot_id: Optional[int] = None
    client_id: Optional[str] = None

    @classmethod
    def from_latency_data(cls, data: LatencyDataLike, metric_type: str) -> "LatencyMetric":
        """Create from LatencyData model."""
        # Determine the specific latency value based on metric type
        latency_ms = None
        if metric_type == "maker_orderbook_fetch" and data.orderbook_latency_maker:
            latency_ms = int(data.orderbook_latency_maker)
        elif metric_type == "maker_order_ack" and data.maker_latency:
            latency_ms = int(data.maker_latency)
        elif metric_type == "cancel_request_send" and data.cancel_request_latency:
            latency_ms = int(data.cancel_request_latency)
        elif metric_type == "trade_cycle" and data.cycle_latency:
            latency_ms = int(data.cycle_latency)
        elif metric_type == "maker_fill_ws_delay" and data.fill_notification_latency_ms:
            latency_ms = int(data.fill_notification_latency_ms)

        return cls(
            time=(datetime.fromtimestamp(data.timestamp / 1000) if data.timestamp else datetime.now()),
            metric_type=metric_type,
            exchange_maker=data.maker_exchange,
            exchange_taker=data.taker_exchange,
            contract=data.maker_contract,
            latency_ms=latency_ms,
            state_transitions=data.state_timestamps or {},
            route_id=data.route_id,
            bot_id=data.bot_id,
            client_id=data.client_id,
        )

    @classmethod
    def create_multiple_from_latency_data(cls, data: LatencyDataLike) -> List["LatencyMetric"]:
        """Create multiple metrics from a single LatencyData object."""
        metrics = []

        # Maker orderbook fetch latency
        if data.orderbook_latency_maker is not None:
            metrics.append(cls.from_latency_data(data, "maker_orderbook_fetch"))

        # Maker order acknowledgment latency
        if data.maker_latency is not None:
            metrics.append(cls.from_latency_data(data, "maker_order_ack"))

        # Cancel request send latency
        if data.cancel_request_latency is not None:
            metrics.append(cls.from_latency_data(data, "cancel_request_send"))

        # Full trade cycle latency
        if data.cycle_latency is not None:
            metrics.append(cls.from_latency_data(data, "trade_cycle"))

        # Maker fill WebSocket delay (blindness window)
        if data.fill_notification_latency_ms is not None:
            metrics.append(cls.from_latency_data(data, "maker_fill_ws_delay"))

        return metrics

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Generate insert query and parameters."""
        query = """
            INSERT INTO latency_metrics
            (time, metric_type, exchange_maker, exchange_taker,
             contract, latency_ms, state_transitions, route_id, bot_id, client_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            self.time,
            self.metric_type,
            self.exchange_maker,
            self.exchange_taker,
            self.contract,
            self.latency_ms,
            Jsonb(self.state_transitions) if self.state_transitions else None,
            self.route_id,
            self.bot_id,
            self.client_id,
        )

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get query for batch inserts."""
        return """
            INSERT INTO latency_metrics
            (time, metric_type, exchange_maker, exchange_taker,
             contract, latency_ms, state_transitions, route_id, bot_id, client_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    def to_batch_params(self) -> Tuple[Any, ...]:
        """Convert to parameters tuple for batch insert."""
        return (
            self.time,
            self.metric_type,
            self.exchange_maker,
            self.exchange_taker,
            self.contract,
            self.latency_ms,
            Jsonb(self.state_transitions) if self.state_transitions else None,
            self.route_id,
            self.bot_id,
            self.client_id,
        )
