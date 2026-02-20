"""Database writer for real-time data insertion with batching and async support."""

import queue
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from data_models.logging import debug, error, info, initialize_logging_context
from data_models.database.core.db_config import AnalyticsDatabaseManager, get_analytics_db_manager
from data_models.database.tables import (
    AccountBalance,
    BlockTrade,
    BotHealthStatus,
    BotRunUpdate,
    ErrorLog,
    FundingEngineAdjustment,
    FundingEngineSpreadImpact,
    FundingRateSnapshot,
    LatencyMetric,
    MarketData,
    OpenInterestSnapshot,
    OrderExecution,
    PositionHistory,
    PositionSnapshot,
    PricingSpreadSnapshot,
    ReferencePrice,
    SpreadNormalizationEvent,
    VolumeSnapshot,
)
from data_models.database.tables.protocols import BatchInsertable, BatchUpsertable
from data_models.database.types.persistence_protocols import BrokerMarketDataLike


class DatabaseWriter:
    """Handles efficient database writes with batching and buffering.

    NOTE: This writer uses the ANALYTICS database for all writes.
    All data written here (orders, trades, positions, balances, metrics)
    goes to the analytics database, not the credentials database.
    """

    def __init__(
        self,
        batch_size: int = 5,
        flush_interval: float = 0.5,
        max_queue_size: int = 10000,
    ) -> None:
        """
        Initialize database writer.

        Args:
            batch_size: Number of records to batch before writing
            flush_interval: Seconds between forced flushes
            max_queue_size: Maximum number of records to queue
        """
        # Log initialization parameters for debugging
        info(
            f"Initializing with batch_size={batch_size}, " f"flush_interval={flush_interval}, max_queue_size={max_queue_size}"
        )

        # Ensure batch_size is never None
        self.batch_size = batch_size if batch_size is not None else 5
        self.flush_interval = flush_interval if flush_interval is not None else 0.5
        self.max_queue_size = max_queue_size if max_queue_size is not None else 10000

        # Separate queues for each data type
        # Use 0 for unlimited queue size if max_queue_size is None
        # Queue with maxsize=0 means unlimited size
        queue_size = self.max_queue_size if self.max_queue_size is not None else 0

        self.queues: Dict[str, queue.Queue[Any]] = {
            "order_executions": queue.Queue(maxsize=queue_size),
            "latency_metrics": queue.Queue(maxsize=queue_size),
            "position_snapshots": queue.Queue(maxsize=queue_size),
            "market_data": queue.Queue(maxsize=queue_size),
            "block_trades": queue.Queue(maxsize=queue_size),
            "account_balances": queue.Queue(maxsize=queue_size),
            "error_logs": queue.Queue(maxsize=queue_size),
            "position_history": queue.Queue(maxsize=queue_size),
            "bot_run_updates": queue.Queue(maxsize=queue_size),
            "bot_health_status": queue.Queue(maxsize=queue_size),
            "reference_prices": queue.Queue(maxsize=queue_size),
            "funding_rates": queue.Queue(maxsize=queue_size),
            # Broker market data snapshots (from WebSocket streams)
            "broker_funding_rates": queue.Queue(maxsize=queue_size),
            "broker_mark_prices": queue.Queue(maxsize=queue_size),
            # Funding engine derived data
            "funding_engine_adjustments": queue.Queue(maxsize=queue_size),
            "funding_engine_spread_impacts": queue.Queue(maxsize=queue_size),
            # Market metrics snapshots
            "open_interest_snapshots": queue.Queue(maxsize=queue_size),
            "volume_snapshots": queue.Queue(maxsize=queue_size),
            # Pricing spread data
            "pricing_spread_snapshots": queue.Queue(maxsize=queue_size),
            "spread_normalization_events": queue.Queue(maxsize=queue_size),
        }

        # Batches for each queue (persist across iterations)
        self._batches: Dict[str, List[Any]] = {
            "order_executions": [],
            "latency_metrics": [],
            "position_snapshots": [],
            "market_data": [],
            "block_trades": [],
            "account_balances": [],
            "error_logs": [],
            "position_history": [],
            "bot_run_updates": [],
            "bot_health_status": [],
            "reference_prices": [],
            "funding_rates": [],
            # Broker market data snapshots
            "broker_funding_rates": [],
            "broker_mark_prices": [],
            # Funding engine derived data
            "funding_engine_adjustments": [],
            "funding_engine_spread_impacts": [],
            # Market metrics snapshots
            "open_interest_snapshots": [],
            "volume_snapshots": [],
            # Pricing spread data
            "pricing_spread_snapshots": [],
            "spread_normalization_events": [],
        }

        self.db_manager: Optional[AnalyticsDatabaseManager] = None
        self._running: bool = False
        self._writer_thread: Optional[threading.Thread] = None
        self._last_flush_time: float = time.time()

    def start(self) -> None:
        """Start the database writer thread."""
        if self._running:
            return

        # Use analytics database manager for all writes
        self.db_manager = get_analytics_db_manager()
        if not self.db_manager.pool:
            error("Analytics database not initialized")
            return

        self._running = True
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer_thread.start()
        info("Started database writer thread")

    def stop(self) -> None:
        """Stop the database writer thread and flush remaining data."""
        if not self._running:
            return

        self._running = False

        # Flush all remaining data
        self._flush_all_queues()

        if self._writer_thread:
            self._writer_thread.join(timeout=5)
            self._writer_thread = None

        info("Stopped database writer thread")

    def write_order_execution(self, order_execution: OrderExecution) -> None:
        """Queue an order execution for writing."""
        try:
            # Log order_execution details for debugging
            debug(
                f"Queueing order execution: order_id={order_execution.order_id}, "
                f"internal_id={order_execution.internal_id}, "
                f"status={order_execution.status}"
            )

            # Extra logging to trace the error
            queue_obj = self.queues.get("order_executions")
            if queue_obj is None:
                error("order_executions queue is None!")
                return

            debug(f"Queue maxsize={queue_obj.maxsize}, qsize={queue_obj.qsize()}")

            queue_obj.put_nowait(order_execution)

        except queue.Full:
            error("Order execution queue full, dropping record")
        except TypeError as e:
            if "NoneType" in str(e):
                error(
                    f"NoneType comparison error in put_nowait: {str(e)}\n"
                    f"Queue maxsize: {self.queues['order_executions'].maxsize}\n"
                    f"Stack trace:\n{''.join(traceback.format_stack())}\n"
                    f"Exception trace:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                )
            else:
                raise
        except Exception as e:
            error(f"Error queuing order execution: {str(e)}, " f"order_execution={order_execution}")

    def write_latency_metrics(self, metrics: Union[LatencyMetric, List[LatencyMetric]]) -> None:
        """Queue latency metrics for writing."""
        if isinstance(metrics, LatencyMetric):
            metrics = [metrics]

        for metric in metrics:
            try:
                self.queues["latency_metrics"].put_nowait(metric)
            except queue.Full:
                error("Latency metrics queue full, dropping record")
                break

    def write_position_snapshot(self, snapshot: PositionSnapshot) -> None:
        """Queue a position snapshot for writing."""
        try:
            self.queues["position_snapshots"].put_nowait(snapshot)
        except queue.Full:
            error("Position snapshot queue full, dropping record")

    def write_market_data(self, data: MarketData) -> None:
        """Queue market data for writing."""
        try:
            self.queues["market_data"].put_nowait(data)
        except queue.Full:
            error("Market data queue full, dropping record")

    def write_block_trade(self, trade: BlockTrade) -> None:
        """Queue a block trade for writing."""
        try:
            self.queues["block_trades"].put_nowait(trade)
        except queue.Full:
            error("Block trade queue full, dropping record")

    def write_account_balance(self, balance: AccountBalance) -> None:
        """Queue an account balance for writing."""
        try:
            self.queues["account_balances"].put_nowait(balance)
        except queue.Full:
            error("Account balance queue full, dropping record")

    def write_error_log(self, error_log: ErrorLog) -> None:
        """Queue an error log for writing."""
        # Only write ERROR level logs, skip all others
        if error_log.level != "ERROR":
            return

        try:
            self.queues["error_logs"].put_nowait(error_log)
        except queue.Full:
            # Don't log error about error queue being full to avoid infinite loop
            pass

    def write_position_history(self, position_history: PositionHistory) -> None:
        """Queue a position history record for writing."""
        try:
            self.queues["position_history"].put_nowait(position_history)
        except queue.Full:
            error("Position history queue full, dropping record")

    def write_bot_run_update(self, bot_run_update: BotRunUpdate) -> None:
        """Queue a bot run update for writing."""
        try:
            self.queues["bot_run_updates"].put_nowait(bot_run_update)
        except queue.Full:
            error("Bot run update queue full, dropping record")

    def write_bot_health_status(self, health_status: BotHealthStatus) -> None:
        """Queue a bot health status for writing.

        Note: bot_id is a logical reference only (no FK constraint) since
        bots table is in credentials DB and bot_health_status is in analytics DB.
        """
        try:
            self.queues["bot_health_status"].put_nowait(health_status)
        except queue.Full:
            error("Bot health status queue full, dropping record")

    def write_reference_price(self, reference_price: ReferencePrice) -> None:
        """Queue a reference price for writing (upsert).

        Uses PostgreSQL's ON CONFLICT clause to update if exists, insert if not.
        """
        try:
            self.queues["reference_prices"].put_nowait(reference_price)
        except queue.Full:
            error("Reference price queue full, dropping record")

    def write_funding_rate_snapshot(self, snapshot: FundingRateSnapshot) -> None:
        """Queue a funding rate snapshot for writing."""
        try:
            self.queues["funding_rates"].put_nowait(snapshot)
        except queue.Full:
            error("Funding rate snapshot queue full, dropping record")

    def write_funding_rate_snapshots(self, snapshots: List[FundingRateSnapshot]) -> None:
        """Queue multiple funding rate snapshots for writing (bulk operation)."""
        for snapshot in snapshots:
            try:
                self.queues["funding_rates"].put_nowait(snapshot)
            except queue.Full:
                error("Funding rate snapshot queue full, dropping record")
                break

    def write_broker_funding_rate(self, funding_rate: BrokerMarketDataLike, exchange: str) -> None:
        """Queue a broker FundingRate model for database insertion.

        Args:
            funding_rate: FundingRate Pydantic model from broker
            exchange: Exchange name (e.g., "binance_futures", "bybit")
        """
        try:
            self.queues["broker_funding_rates"].put_nowait((funding_rate, exchange))
        except queue.Full:
            error("Broker funding rate queue full, dropping record")

    def write_broker_mark_price(self, mark_price: BrokerMarketDataLike, exchange: str) -> None:
        """Queue a broker MarkPrice model for database insertion.

        Args:
            mark_price: MarkPrice Pydantic model from broker
            exchange: Exchange name (e.g., "binance_futures", "bybit")
        """
        try:
            self.queues["broker_mark_prices"].put_nowait((mark_price, exchange))
        except queue.Full:
            error("Broker mark price queue full, dropping record")

    def write_funding_engine_adjustment(self, adjustment: FundingEngineAdjustment) -> None:
        """Queue a funding engine adjustment for writing.

        Args:
            adjustment: FundingEngineAdjustment model with price adjustment data
        """
        try:
            self.queues["funding_engine_adjustments"].put_nowait(adjustment)
        except queue.Full:
            error("Funding engine adjustment queue full, dropping record")

    def write_funding_engine_spread_impact(self, impact: FundingEngineSpreadImpact) -> None:
        """Queue a funding engine spread impact for writing.

        Args:
            impact: FundingEngineSpreadImpact model with spread impact data
        """
        try:
            self.queues["funding_engine_spread_impacts"].put_nowait(impact)
        except queue.Full:
            error("Funding engine spread impact queue full, dropping record")

    def write_open_interest_snapshot(
        self,
        timestamp: datetime,
        exchange: str,
        symbol: str,
        open_interest: float,
        open_interest_value: Optional[float] = None,
    ) -> None:
        """Queue an open interest snapshot for writing.

        Args:
            timestamp: Snapshot timestamp
            exchange: Exchange name (e.g., "binance_futures")
            symbol: Helena internal contract format (e.g., "BTC_USD")
            open_interest: Open interest value
            open_interest_value: Optional USD value of open interest
        """
        try:
            snapshot = OpenInterestSnapshot.from_monitor_data(
                timestamp=timestamp,
                exchange=exchange,
                symbol=symbol,
                open_interest=open_interest,
                open_interest_value=open_interest_value,
            )
            self.queues["open_interest_snapshots"].put_nowait(snapshot)
        except queue.Full:
            error("Open interest snapshot queue full, dropping record")

    def write_volume_snapshot(
        self,
        timestamp: datetime,
        exchange: str,
        symbol: str,
        volume_24h: float,
        volume_24h_base: Optional[float] = None,
    ) -> None:
        """Queue a volume snapshot for writing.

        Args:
            timestamp: Snapshot timestamp
            exchange: Exchange name (e.g., "binance_futures")
            symbol: Helena internal contract format (e.g., "BTC_USD")
            volume_24h: 24-hour volume in quote currency (USD/USDT)
            volume_24h_base: Optional 24-hour volume in base currency
        """
        try:
            snapshot = VolumeSnapshot.from_monitor_data(
                timestamp=timestamp,
                exchange=exchange,
                symbol=symbol,
                volume_24h=volume_24h,
                volume_24h_base=volume_24h_base,
            )
            self.queues["volume_snapshots"].put_nowait(snapshot)
        except queue.Full:
            error("Volume snapshot queue full, dropping record")

    def write_pricing_spread_snapshot(self, snapshot: PricingSpreadSnapshot) -> None:
        """Queue a pricing spread snapshot for writing.

        Args:
            snapshot: PricingSpreadSnapshot model with real-time spread data
        """
        try:
            self.queues["pricing_spread_snapshots"].put_nowait(snapshot)
        except queue.Full:
            error("Pricing spread snapshot queue full, dropping record")

    def write_spread_normalization_event(self, event: SpreadNormalizationEvent) -> None:
        """Queue a spread normalization event for writing.

        Args:
            event: SpreadNormalizationEvent model with mean reversion data
        """
        try:
            self.queues["spread_normalization_events"].put_nowait(event)
        except queue.Full:
            error("Spread normalization event queue full, dropping record")

    def _writer_loop(self) -> None:
        """Main writer loop that processes queues and writes to database."""
        # Initialize logging context for this thread
        initialize_logging_context("database_writer")

        self._last_flush_time = time.time()
        info(f"Writer loop started, batch_size={self.batch_size}, flush_interval={self.flush_interval}")

        while self._running:
            try:
                # Check if it's time to flush
                current_time = time.time()
                should_flush = (current_time - self._last_flush_time) >= self.flush_interval
                if should_flush:
                    debug(f"Time to flush! Elapsed: {current_time - self._last_flush_time:.2f}s")

                # Process each queue
                for queue_name, queue_obj in self.queues.items():
                    # Get the persistent batch for this queue
                    batch = self._batches[queue_name]

                    # Collect items from queue up to batch size
                    while len(batch) < self.batch_size and not queue_obj.empty():
                        try:
                            item = queue_obj.get_nowait()
                            batch.append(item)
                            debug(f"Added item to {queue_name} batch, size now: {len(batch)}")
                        except queue.Empty:
                            break

                    # Write batch if we have items and (batch is full or time to flush)
                    if batch and (len(batch) >= self.batch_size or should_flush):
                        if len(batch) > 1:
                            debug(f"Writing batch of {len(batch)} items from {queue_name}")
                        else:
                            debug(f"Writing single item to {queue_name}")
                        self._write_batch(queue_name, batch)
                        # Clear the batch after writing
                        self._batches[queue_name] = []

                if should_flush:
                    self._last_flush_time = current_time

                # Small sleep to prevent CPU spinning
                time.sleep(0.01)

            except Exception as e:
                error(f"Error in writer loop: {str(e)}")
                time.sleep(1)  # Back off on error

    def _write_batch(self, table_name: str, batch: List[Any]) -> None:
        """Write a batch of records to the database."""
        if not batch or not self.db_manager:
            return

        try:
            # Dispatch to specialized handlers based on table type
            if table_name == "bot_run_updates":
                self._write_bot_run_updates_batch(batch)
            elif table_name == "reference_prices":
                self._write_reference_prices_batch(batch, table_name)
            elif table_name in ("broker_funding_rates", "broker_mark_prices"):
                self._write_broker_market_data_batch(batch, table_name)
            else:
                self._write_standard_batch(batch, table_name)

        except Exception as e:
            self._handle_write_error(e, batch, table_name)

    def _write_bot_run_updates_batch(self, batch: List[Any]) -> None:
        """Write bot run updates (individual UPDATE queries)."""
        # db_manager validated by caller (_write_batch)
        assert self.db_manager is not None

        for item in batch:
            query, params = item.to_insert_query()  # Actually returns UPDATE query
            try:
                self.db_manager.execute(query, params)
            except Exception as e:
                error(f"Failed to update bot run: {str(e)}")
                error(f"Query: {query}, Params: {params}")

        info(f"Successfully processed {len(batch)} bot run updates")

    def _write_reference_prices_batch(self, batch: List[Any], table_name: str) -> None:
        """Write reference prices (batch UPSERT)."""
        # db_manager validated by caller (_write_batch)
        assert self.db_manager is not None

        first_item = batch[0]
        if not isinstance(first_item, BatchUpsertable):
            error(f"No batch_upsert_query method for {table_name}")
            return

        query = first_item.batch_upsert_query()

        # Convert batch to parameters (upsert needs created_at and updated_at)
        params_list = [item.to_upsert_query()[1] for item in batch]

        self.db_manager.execute_many(query, params_list)
        info(f"Successfully upserted {len(batch)} reference prices")

    def _write_broker_market_data_batch(self, batch: List[Any], table_name: str) -> None:
        """Write broker market data (tuples of model, exchange)."""
        # db_manager validated by caller (_write_batch)
        assert self.db_manager is not None

        model, _ = batch[0]
        query = model.batch_insert_query()

        # Convert batch to parameters (model.to_insert_query needs exchange)
        params_list = [m.to_insert_query(ex)[1] for m, ex in batch]

        self.db_manager.execute_many(query, params_list)
        if len(batch) > 1:
            debug(f"Successfully wrote {len(batch)} broker market data records to {table_name}")
        else:
            debug(f"Successfully wrote 1 broker market data record to {table_name}")

    def _write_standard_batch(self, batch: List[Any], table_name: str) -> None:
        """Write standard batch (BatchInsertable items)."""
        # db_manager validated by caller (_write_batch)
        assert self.db_manager is not None

        first_item = batch[0]
        if not isinstance(first_item, BatchInsertable):
            error(f"No batch_insert_query method for {table_name}")
            return

        query = first_item.batch_insert_query()
        params_list = [item.to_insert_query()[1] for item in batch]

        self.db_manager.execute_many(query, params_list)

        if len(batch) > 1:
            debug(f"Successfully wrote {len(batch)} records to {table_name}")
        else:
            debug(f"Successfully wrote 1 record to {table_name}")

    def _handle_write_error(self, e: Exception, batch: List[Any], table_name: str) -> None:
        """Handle errors during batch write operations."""
        # Handle UniqueViolation separately (expected for order_executions duplicates)
        is_unique_violation = "UniqueViolation" in type(e).__name__ or "unique constraint" in str(e).lower()

        if is_unique_violation:
            debug(
                f"Skipped {len(batch)} duplicate(s) in {table_name} " "(UNIQUE index prevented duplicates - expected behavior)"
            )
        else:
            error(f"Failed to write batch to {table_name}: {str(e)}")
            error(f"Error type: {type(e).__name__}")

            # Log the first item for debugging (only for real errors)
            if not batch:
                return

            error(f"First item in failed batch: {batch[0]}")
            try:
                query, params = batch[0].to_insert_query()
                error(f"Query: {query}")
                error(f"Params: {params}")
                for i, param in enumerate(params):
                    debug(f"Param[{i}]: {param} (type: {type(param).__name__})")
            except Exception as qe:
                error(f"Failed to get query/params: {str(qe)}")

    def _flush_all_queues(self) -> None:
        """Flush all queues to database."""
        info("Flushing all queues...")

        for queue_name, queue_obj in self.queues.items():
            # Start with any items already in the persistent batch
            batch = self._batches[queue_name][:]

            # Drain the queue
            while not queue_obj.empty():
                try:
                    item = queue_obj.get_nowait()
                    batch.append(item)

                    # Write in chunks to avoid memory issues
                    if len(batch) >= self.batch_size:
                        self._write_batch(queue_name, batch)
                        batch = []

                except queue.Empty:
                    break

            # Write remaining items
            if batch:
                self._write_batch(queue_name, batch)

            # Clear the persistent batch
            self._batches[queue_name] = []


# Global database writer instance
_db_writer: Optional[DatabaseWriter] = None


def get_database_writer() -> DatabaseWriter:
    """Get or create the global database writer instance."""
    global _db_writer
    if _db_writer is None:
        _db_writer = DatabaseWriter()
    return _db_writer


def start_database_writer() -> None:
    """Start the global database writer."""
    writer = get_database_writer()
    writer.start()


def stop_database_writer() -> None:
    """Stop the global database writer."""
    global _db_writer
    if _db_writer:
        _db_writer.stop()
        _db_writer = None
