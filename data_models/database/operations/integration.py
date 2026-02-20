"""Integration module to connect database writer with bot components."""

from typing import Any, Dict, List, Optional, Set

from data_models.logging import debug, error, info, warning
from data_models.models.reporting.report_models import BlockTradeInfo
from data_models.database.core.db_config import get_analytics_db_manager
from data_models.database.operations.writer import DatabaseWriter, get_database_writer
from data_models.database.tables import (
    AccountBalance,
    BlockTrade,
    ErrorLog,
    LatencyMetric,
    MarketData,
    OrderExecution,
    PositionHistory,
    PositionSnapshot,
    ReferencePrice,
)
from data_models.database.types.persistence_protocols import BalanceLike, LatencyDataLike, OrderLike, OrderbookLike, PositionLike


def _get_exchange_name_from_gateway(gateway: Any) -> str:
    """Get exchange name from gateway.

    Returns the exchange_name property as a string.
    """
    name = gateway.exchange_name
    # Handle ExchangeName enum
    return str(name.value) if hasattr(name, "value") else str(name)


def _get_balances_from_gateway(gateway: Any) -> List[BalanceLike]:
    """Get balances from gateway.

    Returns balances via the gateway's balances service.
    """
    if gateway.balances is None:
        return []
    result: List[BalanceLike] = gateway.balances.get_all_balances()
    return result


def _get_positions_from_gateway(gateway: Any) -> List[PositionLike]:
    """Get positions from gateway.

    Returns positions via the gateway's positions service.
    Returns empty list for spot exchanges (no positions service).
    """
    from data_models.logging import debug, info

    if gateway.positions is None:
        # Spot exchange - no positions
        debug(f"[DatabaseIntegration] gateway.positions is None for {gateway.exchange_name}")
        return []

    info(f"[DatabaseIntegration] Fetching positions from {gateway.exchange_name} via gateway.positions.get_all_positions()")
    result: List[PositionLike] = gateway.positions.get_all_positions()
    info(f"[DatabaseIntegration] Got {len(result)} positions from {gateway.exchange_name}")
    return result


def _get_orderbook_from_gateway(gateway: Any, contract: str) -> Optional[OrderbookLike]:
    """Get orderbook from gateway.

    Returns orderbook via the gateway's market_data service.
    """
    if gateway.market_data is None:
        return None
    result: Optional[OrderbookLike] = gateway.market_data.get_orderbook(contract)
    return result


STABLECOIN_ASSETS = {"USDT", "USDC", "USD", "DAI", "BUSD", "USDS"}


class DatabaseIntegration:
    """Integrates database writing into the bot's data flow."""

    def __init__(self, enabled: bool = True, bot_id: Optional[int] = None) -> None:
        """
        Initialize database integration.

        Args:
            enabled: Whether database writing is enabled
            bot_id: Bot ID for this process (used as default for all writes)
        """
        self.enabled = enabled
        self.bot_id = bot_id  # Stored at process level - applies to all writes
        self.writer: Optional[DatabaseWriter] = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Ensure the database connections are initialized.

        NOTE: This checks the ANALYTICS database since DatabaseWriter uses analytics DB.
        The credentials database should also be initialized separately for bot config.
        """
        if self._initialized or not self.enabled:
            return self.enabled

        try:
            # Database should be initialized by initialize_database_integration
            # which passes the config from JSON file
            from data_models.database.core.db_config import get_analytics_db_manager

            analytics_db_manager = get_analytics_db_manager()

            if analytics_db_manager.pool is None:
                # If pool is not initialized, we're being called directly
                # This shouldn't happen in normal flow, but we'll handle it gracefully
                debug("[DatabaseIntegration] Analytics database pool not initialized yet")
                return False

            self.writer = get_database_writer()
            self.writer.start()
            self._initialized = True
            info("[DatabaseIntegration] Initialized and enabled (analytics database)")
            return True
        except Exception as e:
            error(f"[DatabaseIntegration] Failed to initialize: {str(e)}")
            self.enabled = False
            return False

    def write_order(
        self,
        order: OrderLike,
        exchange: str,
        route_id: Optional[int] = None,
        bot_id: Optional[int] = None,
        block_id: Optional[str] = None,
    ) -> None:
        """Write order execution to database (async via queue).

        Args:
            order: Order to record
            exchange: Exchange name
            route_id: Legacy route ID (deprecated, use bot_id)
            bot_id: Bot ID for this order (defaults to process-level bot_id if not provided)
            block_id: Block trade ID for reconciliation
        """
        if not self._ensure_initialized():
            return

        if self.writer is None:
            error("[DatabaseIntegration] Writer not initialized")
            return

        try:
            # Use process-level bot_id as default if not provided
            # This ensures all orders written by this bot have the correct bot_id
            # even if the caller doesn't explicitly pass it (e.g., WebSocket race condition)
            effective_bot_id = bot_id if bot_id is not None else self.bot_id

            # Pass bot_id and block_id to OrderExecution
            order_exec = OrderExecution.from_order(order, exchange, route_id, effective_bot_id, block_id)
            # Non-blocking queue - returns immediately
            self.writer.write_order_execution(order_exec)
        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write order: {str(e)}")

    def write_orderbook(self, orderbook: OrderbookLike, exchange: str) -> None:
        """Write orderbook snapshot to database."""
        if not self._ensure_initialized():
            return

        if self.writer is None:
            error("[DatabaseIntegration] Writer not initialized")
            return

        try:
            market_data = MarketData.from_orderbook(orderbook, exchange)
            self.writer.write_market_data(market_data)
        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write orderbook: {str(e)}")

    def write_position(self, position: PositionLike, exchange: str, account_id: Optional[int] = None) -> None:
        """Write position snapshot to database.

        Note: Position snapshots are only relevant for futures exchanges.
        Spot exchanges don't have concepts like mark_price, liquidation_price,
        or unrealized_pnl, so we skip writing positions for spot trading.

        Args:
            position: Position model to write
            exchange: Exchange name
            account_id: Optional account ID to link position to accounts table
        """
        if not self._ensure_initialized():
            return

        # Skip position snapshots for spot exchanges
        # Position model fields like mark_price, liquidation_price, unrealized_pnl
        # are only meaningful for futures/derivatives trading
        if "_spot" in exchange.lower() or "spot" in exchange.lower() or "ripio" in exchange.lower():
            debug(f"[DatabaseIntegration] Skipping position snapshot for spot exchange: {exchange}")
            return

        if self.writer is None:
            error("[DatabaseIntegration] Writer not initialized")
            return

        try:
            # Pass account_id for cross-database reference
            snapshot = PositionSnapshot.from_position(position, exchange, account_id=account_id)
            self.writer.write_position_snapshot(snapshot)
        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write position: {str(e)}")

    def write_balance(
        self, balance: BalanceLike, exchange: str, usd_value: Optional[float] = None, account_id: Optional[int] = None
    ) -> None:
        """Write account balance to database.

        Args:
            balance: Balance model to write
            exchange: Exchange name
            usd_value: Optional USD value of balance
            account_id: Optional account ID to link balance to accounts table
        """
        if not self._ensure_initialized():
            return

        if self.writer is None:
            error("[DatabaseIntegration] Writer not initialized")
            return

        try:
            # Pass account_id for cross-database reference
            account_balance = AccountBalance.from_balance(balance, exchange, usd_value, account_id=account_id)
            self.writer.write_account_balance(account_balance)
        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write balance: {str(e)}")

    def write_all_balances(self, exchange_interface: Any, account_id: Optional[int] = None) -> int:
        """Fetch and write all balances from an exchange gateway.

        Args:
            exchange_interface: Gateway instance to fetch balances from
            account_id: Optional account ID to link balances to accounts table

        Returns:
            Number of balances written
        """
        if not self._ensure_initialized():
            return 0

        try:
            exchange_name = _get_exchange_name_from_gateway(exchange_interface)
            balances = _get_balances_from_gateway(exchange_interface)

            # DIAGNOSTIC: Log raw balance count
            info(
                f"[DatabaseIntegration] Got {len(balances) if balances else 0} raw balances from {exchange_name} (account_id={account_id})"
            )

            # Load reference prices for USD value computation
            price_map = self._get_reference_price_map()

            count = 0
            zero_count = 0
            for balance in balances:
                # Skip zero balances to reduce noise
                if balance.total and balance.total > 0:
                    usd_value = self._compute_usd_value(balance.currency, balance.total, price_map)
                    self.write_balance(balance, exchange_name, usd_value=usd_value, account_id=account_id)
                    count += 1
                else:
                    zero_count += 1

            # DIAGNOSTIC: Log filtering results
            if len(balances) > 0:
                info(f"[DatabaseIntegration]  Filtered: {count} with total>0, {zero_count} with total=0 or None")

            if count > 0:
                info(f"[DatabaseIntegration] Wrote {count} balances for {exchange_name} (account_id={account_id})")
            elif len(balances) == 0:
                warning(
                    f"[DatabaseIntegration] WARNING: get_balances() returned EMPTY LIST for {exchange_name} (account_id={account_id})"
                )
            else:
                warning(
                    f"[DatabaseIntegration] WARNING: All {len(balances)} balances had total=0, "
                    f"none written for {exchange_name} (account_id={account_id})"
                )

            return count

        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write all balances: {str(e)}")
            return 0

    def _get_reference_price_map(self) -> Dict[str, float]:
        """Load reference prices as {asset: price} lookup.

        Queries all rows from reference_prices table and builds a dict
        mapping base asset to USD price. For assets with multiple exchange
        entries, picks the first encountered (prices are close enough).
        Matches USD, USDT, and USDC denominated contracts.
        """
        try:
            analytics_db = get_analytics_db_manager()
            query = """
                SELECT contract, price
                FROM reference_prices
                WHERE SPLIT_PART(contract, '_', 2) IN ('USD', 'USDT', 'USDC')
            """
            with analytics_db.get_cursor(commit=False) as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

            price_map: Dict[str, float] = {}
            for row in rows:
                contract = row["contract"]
                parts = contract.split("_")
                if len(parts) >= 2:
                    asset = parts[0]
                    if asset not in price_map:
                        price_map[asset] = float(row["price"])
            return price_map
        except Exception as e:
            error(f"[DatabaseIntegration] Failed to load reference prices: {str(e)}")
            return {}

    def _compute_usd_value(self, asset: str, amount: float, price_map: Dict[str, float]) -> Optional[float]:
        """Compute USD value for a balance amount.

        Args:
            asset: Asset symbol (e.g., 'BTC', 'USDT')
            amount: Balance amount
            price_map: Mapping of asset to USD price

        Returns:
            USD value if price is known, None otherwise
        """
        if asset in STABLECOIN_ASSETS:
            return amount * 1.0
        price = price_map.get(asset)
        if price:
            return amount * price
        return None

    def write_all_positions(self, exchange_interface: Any, account_id: Optional[int] = None) -> int:
        """Fetch and write all positions from an exchange gateway.

        Also marks positions as closed (size=0) if they exist in the database
        but are no longer reported by the exchange.

        Args:
            exchange_interface: Gateway instance to fetch positions from
            account_id: Optional account ID to link positions to accounts table

        Returns:
            Number of positions written (including closure markers)
        """
        if not self._ensure_initialized():
            return 0

        try:
            exchange_name = _get_exchange_name_from_gateway(exchange_interface)
            positions = _get_positions_from_gateway(exchange_interface)

            # Get contracts currently open on exchange
            open_contracts = {p.contract for p in positions}

            count = 0
            # Write all open positions
            for position in positions:
                self.write_position(position, exchange_name, account_id=account_id)
                count += 1

            # Mark closed positions: positions in DB but not on exchange
            if account_id is not None:
                closed_count = self._mark_closed_positions(exchange_name, account_id, open_contracts)
                count += closed_count

            if count > 0:
                info(f"[DatabaseIntegration] Wrote {count} positions for {exchange_name} (account_id={account_id})")

            return count

        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write all positions: {str(e)}")
            return 0

    def _mark_closed_positions(self, exchange: str, account_id: int, open_contracts: Set[str]) -> int:
        """Mark positions as closed if they exist in DB but not on exchange.

        Creates a position snapshot with size=0 for each closed position.

        Args:
            exchange: Exchange name
            account_id: Account ID to check positions for
            open_contracts: Set of contract names currently open on exchange

        Returns:
            Number of closed positions marked
        """
        try:
            # Query existing positions for this account from analytics DB using raw SQL
            analytics_db = get_analytics_db_manager()

            # Get latest positions for this account (raw SQL via psycopg)
            query = """
                SELECT DISTINCT ON (contract)
                    contract, position_size, entry_price, mark_price
                FROM position_snapshots
                WHERE account_id = %s
                ORDER BY contract, time DESC
            """

            with analytics_db.get_cursor(commit=False) as cursor:
                cursor.execute(query, (account_id,))
                db_positions = cursor.fetchall()

            if self.writer is None:
                error("[DatabaseIntegration] Writer not initialized")
                return 0

            # Find positions that are in DB but not currently open on exchange
            closed_count = 0
            for row in db_positions:
                contract = row["contract"]
                position_size = row["position_size"]

                # Skip if position is already closed (size = 0)
                if position_size is None or float(position_size) == 0:
                    continue

                # Skip if position is still open on exchange
                if contract in open_contracts:
                    continue

                # Position is closed - write a snapshot with size=0
                closed_snapshot = PositionSnapshot.from_values(
                    exchange=exchange,
                    contract=contract,
                    position_size=0.0,
                    entry_price=float(row["entry_price"]) if row["entry_price"] else None,
                    mark_price=float(row["mark_price"]) if row["mark_price"] else None,
                    unrealized_pnl=0.0,
                    account_id=account_id,
                )
                self.writer.write_position_snapshot(closed_snapshot)
                closed_count += 1
                info(f"[DatabaseIntegration] Marked position as closed: {contract} (account_id={account_id})")

            return closed_count

        except Exception as e:
            error(f"[DatabaseIntegration] Failed to mark closed positions: {str(e)}")
            return 0

    def write_reference_price(self, exchange: str, contract: str, orderbook: OrderbookLike) -> None:
        """Write reference price (orderbook mid-price) to database.

        Calculates mid-price from orderbook and writes to reference_prices table.
        Uses upsert logic to update existing price or insert new one.

        Args:
            exchange: Exchange name
            contract: Contract symbol
            orderbook: Orderbook with best bid/ask prices
        """
        if not self._ensure_initialized():
            return

        if self.writer is None:
            error("[DatabaseIntegration] Writer not initialized")
            return

        try:
            # Extract best bid/ask from orderbook
            if not orderbook.bids or not orderbook.asks:
                debug(f"[DatabaseIntegration] Skipping reference price for {contract} - empty orderbook")
                return

            # OrderbookLevel is a Pydantic model with .price and .amount attributes
            best_bid = orderbook.bids[0].price
            best_ask = orderbook.asks[0].price

            # Create ReferencePrice model
            ref_price = ReferencePrice.from_orderbook(
                exchange=exchange,
                contract=contract,
                best_bid=best_bid,
                best_ask=best_ask,
            )

            self.writer.write_reference_price(ref_price)

        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write reference price for {contract}: {str(e)}")

    def write_all_reference_prices(self, exchange_interface: Any, contracts: List[str]) -> int:
        """Fetch orderbooks and write reference prices for all contracts.

        Args:
            exchange_interface: Gateway instance to fetch orderbooks from
            contracts: List of contracts to write prices for (required)

        Returns:
            Number of reference prices written
        """
        if not self._ensure_initialized():
            return 0

        try:
            exchange_name = _get_exchange_name_from_gateway(exchange_interface)

            count = 0
            for contract in contracts:
                try:
                    # Fetch orderbook via helper
                    orderbook = _get_orderbook_from_gateway(exchange_interface, contract)

                    if orderbook:
                        self.write_reference_price(exchange_name, contract, orderbook)
                        count += 1

                except Exception as e:
                    error(f"[DatabaseIntegration] Failed to write reference price for {contract}: {str(e)}")
                    continue

            if count > 0:
                info(f"[DatabaseIntegration] Wrote {count} reference prices for {exchange_name}")

            return count

        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write all reference prices: {str(e)}")
            return 0

    def write_latency_data(self, latency_data: LatencyDataLike) -> None:
        """Write latency metrics to database."""
        if not self._ensure_initialized():
            return

        if self.writer is None:
            error("[DatabaseIntegration] Writer not initialized")
            return

        try:
            metrics = LatencyMetric.create_multiple_from_latency_data(latency_data)
            self.writer.write_latency_metrics(metrics)
        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write latency data: {str(e)}")

    def write_block_trade(self, block_trade_info: BlockTradeInfo, bot_id: Optional[int] = None) -> None:
        """Write block trade to database.

        Args:
            block_trade_info: Trade information to write
            bot_id: Optional bot ID to track which bot executed the trade
        """
        if not self._ensure_initialized():
            return

        if self.writer is None:
            error("[DatabaseIntegration] Writer not initialized")
            return

        try:
            block_trade = BlockTrade.from_block_trade_info(block_trade_info, bot_id=bot_id)
            self.writer.write_block_trade(block_trade)
        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write block trade: {str(e)}")

    def write_error(self, error_log: ErrorLog) -> None:
        """Write error log to database."""
        if not self._ensure_initialized():
            return

        # Only write ERROR level logs to database, skip WARNING and other levels
        if error_log.level != "ERROR":
            return

        if self.writer is None:
            # Don't log error to avoid infinite loop
            return

        try:
            self.writer.write_error_log(error_log)
        except Exception:
            # Don't log error about error logging to avoid infinite loop
            pass

    def write_position_history(
        self,
        timestamp: str,
        maker_exchange: str,
        taker_exchange: str,
        contract: str,
        maker_pos: float,
        taker_pos: float,
    ) -> None:
        """Write position history to database.

        Args:
            timestamp: Timestamp string (will be converted to milliseconds)
            maker_exchange: Name of the maker exchange
            taker_exchange: Name of the taker exchange
            contract: Contract symbol
            maker_pos: Position on maker exchange
            taker_pos: Position on taker exchange
        """
        if not self._ensure_initialized():
            return

        if self.writer is None:
            error("[DatabaseIntegration] Writer not initialized")
            return

        try:
            position_history = PositionHistory.create(
                maker_exchange=maker_exchange,
                taker_exchange=taker_exchange,
                contract=contract,
                maker_position=maker_pos,
                taker_position=taker_pos,
            )
            self.writer.write_position_history(position_history)
        except Exception as e:
            error(f"[DatabaseIntegration] Failed to write position history: {str(e)}")

    def update_bot_run(
        self,
        bot_id: int,
        run_id: int,
        orders_increment: int = 0,
        trades_increment: int = 0,
        pnl_increment: float = 0.0,
    ) -> None:
        """Update bot run statistics (orders count, trades count and P&L).

        Writes to bot_run_stats table in ANALYTICS database using UPSERT.
        The first call creates the row, subsequent calls increment values.

        Args:
            bot_id: ID of the bot to update
            run_id: ID of the current run (from bot_runs table in credentials DB)
            orders_increment: Number of orders to add to the count
            trades_increment: Number of trades (filled orders) to add to the count
            pnl_increment: P&L amount to add to the total
        """
        if not self._ensure_initialized():
            return

        if self.writer is None:
            error("[DatabaseIntegration] Writer not initialized")
            return

        try:
            from data_models.database.tables.bot_run_update import BotRunUpdate

            bot_run_update = BotRunUpdate(
                bot_id=bot_id,
                run_id=run_id,
                orders_increment=orders_increment,
                trades_increment=trades_increment,
                pnl_increment=pnl_increment,
                error_increment=0,
            )

            self.writer.write_bot_run_update(bot_run_update)
            debug(
                f"[DatabaseIntegration] Queued bot run update: bot_id={bot_id}, run_id={run_id}, "
                f"orders_increment={orders_increment}, trades_increment={trades_increment}, pnl_increment={pnl_increment}"
            )

        except Exception as e:
            error(f"[DatabaseIntegration] Failed to update bot run: {str(e)}")


# Global database integration instance
_db_integration: Optional[DatabaseIntegration] = None


def get_database_integration() -> DatabaseIntegration:
    """Get or create the global database integration instance."""
    global _db_integration
    if _db_integration is None:
        _db_integration = DatabaseIntegration()
    return _db_integration


def initialize_database_integration(config: Dict[str, Any], bot_id: Optional[int] = None) -> DatabaseIntegration:
    """Initialize database integration with config.

    NOTE: Initializes BOTH databases:
    - Credentials DB (for bot config, accounts)
    - Analytics DB (for orders, trades, positions, balances)

    Args:
        config: Database configuration dict
        bot_id: Bot ID for this process. When provided, all database writes
                will automatically use this bot_id, eliminating race conditions
                where orders might be written without bot_id linkage.
    """
    global _db_integration

    # Check if database is enabled in config
    db_config = config.get("database", {})
    enabled = db_config.get("enabled", False)

    _db_integration = DatabaseIntegration(enabled=enabled, bot_id=bot_id)

    if bot_id is not None:
        info(f"[DatabaseIntegration] Initialized with bot_id={bot_id} - all writes will use this bot_id")

    if enabled:
        # Initialize BOTH database connections
        from data_models.database.core.db_config import initialize_analytics_database, initialize_database

        # Initialize credentials database (for bot config, accounts, credentials)
        initialize_database(db_config)
        info("[DatabaseIntegration] Credentials database initialized")

        # Initialize analytics database (for orders, trades, positions, balances)
        initialize_analytics_database()  # Uses ANALYTICS_DATABASE_URL env var
        info("[DatabaseIntegration] Analytics database initialized")

        # Start the writer thread (uses analytics DB)
        from data_models.database.operations.writer import start_database_writer

        start_database_writer()

        info("[DatabaseIntegration] Database integration fully initialized (dual databases)")

    return _db_integration


def stop_database_integration() -> None:
    """Stop database integration and flush data."""
    global _db_integration

    if _db_integration and _db_integration.enabled:
        from data_models.database.operations.writer import stop_database_writer

        stop_database_writer()

        info("[DatabaseIntegration] Database integration stopped")

    _db_integration = None
