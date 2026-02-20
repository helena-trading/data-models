"""
Bot Configuration Loader - Loads bot configuration from database
"""

import os
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from data_models.logging import error, info, warning
from data_models.database.loaders.user_settings import get_live_test_config
from data_models.database.tables.account import Account, BotAccount
from data_models.database.tables.bot import Bot
from data_models.models.enums.exchange import ExchangeName, TradeType, get_trade_type
from data_models.models.enums.trading import RoutingType

# Exchange type mapping - defines default trade type for each exchange
EXCHANGE_TYPE_MAP: Dict[ExchangeName, TradeType] = {
    ExchangeName.BINANCE_SPOT: TradeType.SPOT,
    ExchangeName.BINANCE_FUTURES: TradeType.FUTURES,
    ExchangeName.BYBIT: TradeType.FUTURES,
    ExchangeName.HYPERLIQUID: TradeType.FUTURES,
    ExchangeName.RIPIO_TRADE: TradeType.SPOT,
    ExchangeName.LIGHTER: TradeType.FUTURES,
}


def load_bot_config(bot_id: int) -> Optional[Dict[str, Any]]:
    """
    Load bot configuration from database

    Args:
        bot_id: Database ID of the bot

    Returns:
        Bot configuration dictionary or None if not found
    """
    try:
        from urllib.parse import quote

        # Check if AWS Secrets Manager should be used (production)
        use_aws_secrets = os.environ.get("USE_AWS_SECRETS", "false").lower() == "true"

        if use_aws_secrets:
            # Production: Get credentials from AWS Secrets Manager
            from data_models.config.aws_secrets import get_secrets_manager

            secrets_mgr = get_secrets_manager()
            secret_name = os.environ.get("DB_SECRET_NAME", "helena-bot/production/database/app-user")

            info(f"[BotConfigLoader] Fetching DB credentials from Secrets Manager: {secret_name}")
            db_credentials = secrets_mgr.get_secret(secret_name, parse_json=True)

            if not db_credentials or not isinstance(db_credentials, dict):
                raise RuntimeError(f"Failed to retrieve database credentials from {secret_name}")

            # Extract credentials from secret
            db_host = db_credentials.get("host") or os.environ.get("DATABASE_HOST") or os.environ.get("DB_HOST", "localhost")
            db_port = db_credentials.get("port") or int(os.environ.get("DATABASE_PORT", os.environ.get("DB_PORT", "5432")))
            db_name = (
                db_credentials.get("dbname")
                or db_credentials.get("database")
                or os.environ.get("DATABASE_NAME", os.environ.get("DB_NAME", "helena_bot"))
            )
            db_user = db_credentials.get("username") or db_credentials.get("user", "helena")
            db_password = db_credentials.get("password", "")

            # URL-encode password to handle special characters (^, *, #, etc.)
            encoded_password = quote(db_password, safe="")
            database_url = f"postgresql+psycopg://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

            # Export to environment for runner and database integration
            os.environ["DATABASE_URL"] = database_url

            info(f"[BotConfigLoader] Database connection configured from Secrets Manager: {db_user}@{db_host}/{db_name}")

        elif "DATABASE_URL" in os.environ:
            # DATABASE_URL provided (local/dev with simple passwords)
            database_url = os.environ["DATABASE_URL"]

            # Convert to psycopg3 format
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

            # Ensure environment has the updated URL
            os.environ["DATABASE_URL"] = database_url

            info("[BotConfigLoader] Using DATABASE_URL from environment")

        else:
            # Build from individual env vars (local dev)
            db_host = os.environ.get("DB_HOST", "localhost")
            db_port = os.environ.get("DB_PORT", "5432")
            db_name = os.environ.get("DB_NAME", "helena_bot")
            db_user = os.environ.get("DB_USER", "helena")
            db_password = os.environ.get("DB_PASSWORD", "helena123")

            # URL-encode password to handle any special characters
            encoded_password = quote(db_password, safe="")
            database_url = f"postgresql+psycopg://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

            # Export to environment for runner and database integration
            os.environ["DATABASE_URL"] = database_url

            info(f"[BotConfigLoader] Database connection built from env vars: {db_user}@{db_host}/{db_name}")

        # Create database connection
        engine: Engine = create_engine(database_url)
        SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine)

        with SessionLocal() as session:
            # Query bot from database with eager loading of accounts
            bot: Optional[Bot] = session.query(Bot).filter_by(id=bot_id).first()

            if not bot:
                error(f"Bot with ID {bot_id} not found in database")
                return None

            # Extract configuration
            config: Dict[str, Any] = dict(bot.config) if bot.config else {}

            # Add bot metadata
            config["bot_id"] = bot.id
            config["bot_name"] = bot.name
            config["strategy_type"] = bot.strategy_type

            # Load bot accounts if available
            bot_accounts: List[BotAccount] = session.query(BotAccount).filter_by(bot_id=bot_id).all()
            info(f"[BotConfigLoader] Query returned {len(bot_accounts)} BotAccount records for bot_id={bot_id}")

            if bot_accounts:
                config["bot_accounts"] = {}
                for ba in bot_accounts:
                    account: Optional[Account] = session.query(Account).filter_by(id=ba.account_id).first()
                    if account and account.is_active:
                        config["bot_accounts"][ba.role] = {
                            "id": account.id,
                            "name": account.name,
                            "exchange": account.exchange,
                            "account_type": account.account_type,
                            "credential_ref": account.credential_ref,
                            # All credentials use reference-based storage (encrypted in credentials DB)
                            "credential_storage_type": "reference",
                            "is_testnet": account.is_testnet,
                        }
                        info(f"[BotConfigLoader] Loaded account {ba.role}={account.id} ({account.name}) for bot {bot_id}")
                info(f"[BotConfigLoader] Successfully loaded {len(config['bot_accounts'])} account(s) for bot {bot_id}")
            else:
                warning(
                    f"[BotConfigLoader] No bot_accounts found in database for bot_id={bot_id} - DatabaseCollector will not initialize!"
                )

            # Environment variables from config are no longer supported
            # All credentials must come from encrypted database storage

            # Transform config to match the expected format
            transformed_config: Dict[str, Any] = transform_bot_config(config)

            return transformed_config

    except Exception as e:
        error(f"Error loading bot config: {str(e)}")
        raise


def _get_exchange_credentials(exchange_name: str, role: str, bot_accounts: Dict[str, Any]) -> Dict[str, Any]:
    """Get credentials for an exchange, preferring account-based over env_vars."""
    if role in bot_accounts:
        account: Dict[str, Any] = bot_accounts[role]

        # Exact match — both sides are canonical ExchangeName values
        if account["exchange"].lower() == exchange_name.lower():
            result: Dict[str, Any] = {
                "account_id": account.get("id"),
                "credential_ref": account["credential_ref"],
                "credential_storage_type": account.get("credential_storage_type", "reference"),
                "is_testnet": account.get("is_testnet", False),
                "account_type": account.get("account_type", "futures"),
            }
            info(f"[BotConfigLoader] Account credentials for {role}/{exchange_name}: {result}")
            return result

    error(f"No account configured for role {role!r} - credentials must come from encrypted database storage")
    return {}


def _build_exchange_config(exchange_name: str, creds: Dict[str, Any], use_websocket_for_orders: bool) -> Dict[str, Any]:
    """Build exchange configuration dict with credentials."""
    # Get default trade type from enum helper if not in credentials
    # Convert string exchange_name to ExchangeName enum
    exchange_enum = ExchangeName(exchange_name)
    default_trade_type = str(get_trade_type(exchange_enum))
    config: Dict[str, Any] = {
        "name": exchange_name.capitalize(),
        "type": creds.get("account_type", default_trade_type),
        "use_websocket_for_orders": use_websocket_for_orders,
    }

    if "credential_ref" in creds:
        config["account_id"] = creds.get("account_id")
        config["credential_ref"] = creds["credential_ref"]
        config["credential_storage_type"] = creds.get("credential_storage_type", "reference")
        config["is_testnet"] = creds.get("is_testnet", False)
        account_type: str = creds.get("account_type", "futures")
        if account_type == "perpetual":
            account_type = "futures"
        config["type"] = account_type

    return config


def _extract_private_data_hub_settings(bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract private-data-hub settings from data_sources config.

    Private direct WebSocket feeds are deprecated for cross_arb bots.
    This loader now defaults private market data to private_data_hub.
    """
    settings: Dict[str, Any] = {"enabled": True}

    data_sources = bot_config.get("data_sources")
    if not isinstance(data_sources, dict):
        return settings

    private_market_data = data_sources.get("private_market_data")
    if private_market_data is None:
        return settings
    if not isinstance(private_market_data, dict):
        raise ValueError("data_sources.private_market_data must be an object")

    source = str(private_market_data.get("source", "private_data_hub")).strip().lower().replace("-", "_")
    if not source:
        source = "private_data_hub"
    if source != "private_data_hub":
        raise ValueError("data_sources.private_market_data.source must be 'private_data_hub'")

    hub_cfg = private_market_data.get("private_data_hub", {})
    if hub_cfg is None:
        hub_cfg = {}
    if not isinstance(hub_cfg, dict):
        raise ValueError("data_sources.private_market_data.private_data_hub must be an object")

    raw_socket_path = hub_cfg.get("socket_path")
    if raw_socket_path is not None:
        socket_path = str(raw_socket_path).strip()
        if socket_path:
            settings["socket_path"] = socket_path

    # Optional fallback account id; per-exchange account_id takes precedence.
    if hub_cfg.get("account_id") is not None:
        settings["account_id"] = hub_cfg["account_id"]

    return settings


def _apply_private_data_hub_settings(
    exchanges: List[Dict[str, Any]],
    private_data_hub_settings: Dict[str, Any],
) -> None:
    """Attach private-data-hub settings to each transformed exchange config."""
    for exchange_cfg in exchanges:
        exchange_private_cfg: Dict[str, Any] = dict(private_data_hub_settings)
        exchange_account_id = exchange_cfg.get("account_id")

        if exchange_account_id is not None:
            exchange_private_cfg["account_id"] = exchange_account_id

        exchange_cfg["private_data_hub"] = exchange_private_cfg


def _extract_orders_command_hub_settings(bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract orders-command-hub settings from data_sources config."""
    settings: Dict[str, Any] = {"enabled": True}

    data_sources = bot_config.get("data_sources")
    if not isinstance(data_sources, dict):
        return settings

    order_commands = data_sources.get("order_commands")
    if order_commands is None:
        return settings
    if not isinstance(order_commands, dict):
        raise ValueError("data_sources.order_commands must be an object")

    source = str(order_commands.get("source", "orders_command_hub")).strip().lower().replace("-", "_")
    if not source:
        source = "orders_command_hub"
    if source != "orders_command_hub":
        raise ValueError("data_sources.order_commands.source must be 'orders_command_hub'")

    hub_cfg = order_commands.get("orders_command_hub", {})
    if hub_cfg is None:
        hub_cfg = {}
    if not isinstance(hub_cfg, dict):
        raise ValueError("data_sources.order_commands.orders_command_hub must be an object")

    settings["enabled"] = bool(hub_cfg.get("enabled", True))

    raw_socket_path = hub_cfg.get("socket_path")
    if raw_socket_path is not None:
        socket_path = str(raw_socket_path).strip()
        if socket_path:
            settings["socket_path"] = socket_path

    # Optional fallback account id; per-exchange account_id takes precedence.
    if hub_cfg.get("account_id") is not None:
        settings["account_id"] = hub_cfg["account_id"]

    return settings


def _apply_orders_command_hub_settings(
    exchanges: List[Dict[str, Any]],
    orders_command_hub_settings: Dict[str, Any],
) -> None:
    """Attach orders-command-hub settings to each transformed exchange config."""
    for exchange_cfg in exchanges:
        exchange_orders_cfg: Dict[str, Any] = dict(orders_command_hub_settings)
        exchange_account_id = exchange_cfg.get("account_id")

        if exchange_account_id is not None:
            exchange_orders_cfg["account_id"] = exchange_account_id

        exchange_cfg["orders_command_hub"] = exchange_orders_cfg


def _validate_routing_list(routing_list: List[str], contract_list_main: List[str]) -> None:
    """Validate routing list against contract list."""
    if len(routing_list) != len(contract_list_main):
        raise ValueError(
            f"routing_list length ({len(routing_list)}) must match contract lists length ({len(contract_list_main)})"
        )

    for i, routing_type in enumerate(routing_list):
        if not RoutingType.is_valid(routing_type):
            raise ValueError(f"Invalid routing type {routing_type!r} at index {i}. Must be one of: buy, sell, best")


def _validate_final_config(config: Dict[str, Any]) -> None:
    """Validate the final bot configuration."""
    required_fields: List[str] = [
        "bot_id",
        "bot_name",
        "strategy_type",
        "exchanges",
        "contract_list_main",
        "contract_list_sec",
        "routing_list",
        "parameters",  # Hierarchical parameters
    ]

    missing_fields: List[str] = [field for field in required_fields if field not in config or config[field] is None]

    if missing_fields:
        raise ValueError(f"Missing required fields in bot configuration: {', '.join(missing_fields)}")

    # Validate hierarchical parameters have required groups
    params = config.get("parameters", {})
    if "spread" not in params:
        raise ValueError("Missing required 'spread' group in parameters")
    if "sizing" not in params:
        raise ValueError("Missing required 'sizing' group in parameters")

    # Validate exchanges have required fields
    for i, exchange in enumerate(config["exchanges"]):
        if "name" not in exchange:
            raise ValueError(f"Exchange {i} missing 'name' field")
        if "type" not in exchange:
            raise ValueError(f"Exchange {i} missing 'type' field")
        has_credentials: bool = ("api_key" in exchange and exchange["api_key"]) or (
            "credential_ref" in exchange and exchange["credential_ref"]
        )
        if not has_credentials:
            warning(f"Exchange {exchange.get('name', i)} has no credentials configured")


def transform_bot_config(bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform bot configuration from database format to runner format

    Args:
        bot_config: Configuration from database

    Returns:
        Transformed configuration for the runner
    """
    # Check if this is a graph arbitrage or monitoring configuration
    strategy_type: str = bot_config.get("strategy_type", "cross_arb")

    if strategy_type == "graph_arbitrage":
        # Graph arbitrage has a different config structure
        return transform_graph_bot_config(bot_config)

    if strategy_type == "monitoring":
        # Monitoring strategy doesn't need transformation (no maker/taker exchanges)
        info("[BotConfigLoader] Monitoring strategy detected - skipping transformation")
        return bot_config

    # Extract key configuration elements for cross_arb
    # Note: Pydantic validates this automatically when bot_config is created
    exchanges_config: Dict[str, Any] = bot_config.get("exchanges", {})

    maker_exchange: str = exchanges_config["maker"]
    taker_exchange: str = exchanges_config["taker"]

    # Extract contract lists for each exchange
    contract_list_main: Optional[List[str]] = bot_config.get("contract_list_main")
    contract_list_sec: Optional[List[str]] = bot_config.get("contract_list_sec")

    info(f"[BotConfigLoader] transform_bot_config - exchanges_config: {exchanges_config}")

    # Both contract lists are required
    if contract_list_main is None or contract_list_sec is None:
        raise ValueError("Both contract_list_main and contract_list_sec are required in bot configuration")

    info(f"[BotConfigLoader] Contract lists - main: {contract_list_main}, sec: {contract_list_sec}")

    # Note: Pydantic validates contract format automatically when bot_config is created

    # Ensure lists have same length
    if len(contract_list_main) != len(contract_list_sec):
        raise ValueError(
            "contract_list_main and contract_list_sec must have the same length. "
            f"Got main={len(contract_list_main)}, sec={len(contract_list_sec)}"
        )

    parameters: Dict[str, Any] = bot_config.get("parameters", {})
    bot_accounts: Dict[str, Any] = bot_config.get("bot_accounts", {})
    info(f"[BotConfigLoader] bot_accounts: {bot_accounts}")

    # Build exchanges array in the format expected by the runner
    # Hub-only order submission uses websocket command semantics by design.
    use_websocket_for_orders = True
    info("[BotConfigLoader] Enforcing use_websocket_for_orders=True (orders_command_hub)")

    # Build exchanges using helper functions
    maker_creds = _get_exchange_credentials(maker_exchange, "maker", bot_accounts)
    taker_creds = _get_exchange_credentials(taker_exchange, "taker", bot_accounts)

    exchanges: List[Dict[str, Any]] = [
        _build_exchange_config(maker_exchange, maker_creds, use_websocket_for_orders),
        _build_exchange_config(taker_exchange, taker_creds, use_websocket_for_orders),
    ]

    private_data_hub_settings = _extract_private_data_hub_settings(bot_config)
    _apply_private_data_hub_settings(exchanges, private_data_hub_settings)
    info(
        "[BotConfigLoader] Applied private_data_hub settings to exchanges: "
        f"{[exchange.get('name') for exchange in exchanges]}"
    )

    orders_command_hub_settings = _extract_orders_command_hub_settings(bot_config)
    _apply_orders_command_hub_settings(exchanges, orders_command_hub_settings)
    if bool(orders_command_hub_settings.get("enabled", False)):
        info(
            "[BotConfigLoader] Applied orders_command_hub settings to exchanges: "
            f"{[exchange.get('name') for exchange in exchanges]}"
        )

    # Contract lists are already set above based on the configuration format
    info(f"[BotConfigLoader] Final contract lists - main: {contract_list_main}, sec: {contract_list_sec}")

    # Routing list MUST be provided in config
    if "routing_list" not in bot_config:
        raise ValueError("routing_list is required in bot configuration")

    routing_list: List[str] = bot_config["routing_list"]
    _validate_routing_list(routing_list, contract_list_main)
    info(f"[BotConfigLoader] Using routing_list from config: {routing_list}")

    # Build the complete configuration
    config: Dict[str, Any] = {
        # Bot metadata
        "bot_id": bot_config.get("bot_id"),
        "bot_name": bot_config.get("bot_name"),
        "strategy_type": bot_config.get("strategy_type", "cross_arb"),
        # Exchange configuration
        "exchanges": exchanges,
        # Contract configuration
        "contract_list_main": contract_list_main,
        "contract_list_sec": contract_list_sec,
        "routing_list": routing_list,
        # Enable database logging for managed bots
        # Database connection details are in DATABASE_URL environment variable
        # (set above at line 71 from Secrets Manager or line 84 from env)
        # DatabaseConfig.from_env() will parse DATABASE_URL to get all connection details
        "database": bot_config.get(
            "database",
            {
                "enabled": True,
                # Don't specify connection details here - DatabaseConfig.from_env() reads DATABASE_URL
            },
        ),
        # Threading configuration
        "threading": bot_config.get(
            "threading",
            {
                "message_handler_threaded": True,
                "bot_threaded": True,
                "disable_trading_loop": False,
            },
        ),
        # Live testing configuration from user settings or bot config
        "live_testing": bot_config.get("live_testing", get_live_test_config("default")),
        # Monitors configuration
        "monitors": bot_config.get("monitors", {"enabled": False}),
        # Parameter API configuration
        "parameter_api": bot_config.get("parameter_api", {"enabled": False, "polling_interval": 5}),
    }

    # Public/private data source selection (optional, defaults to market_data_hub in runner if omitted)
    if "data_sources" in bot_config:
        config["data_sources"] = bot_config["data_sources"]

    # Check if parameters are in hierarchical format (has 'spread' group)
    if "spread" in parameters:
        # Hierarchical format - pass through as-is
        config["parameters"] = parameters
        info("[BotConfigLoader] Using hierarchical parameter format")
    else:
        # Flat format - should not happen with new system
        raise ValueError(
            "Bot configuration uses deprecated flat parameter format. "
            "Please update to hierarchical format with 'spread', 'sizing' groups."
        )

    # Add other configuration sections if present
    if "position_limits" in bot_config:
        config["position_limits"] = bot_config["position_limits"]

    if "risk_management" in bot_config:
        config["risk_management"] = bot_config["risk_management"]

    if "live_testing" in bot_config:
        config["live_testing"] = bot_config["live_testing"]

    # Validate required fields and exchanges
    _validate_final_config(config)

    # Log the final configuration
    info(
        f"[BotConfigLoader] Final config - contract_list_main: {config.get('contract_list_main')}, "
        f"contract_list_sec: {config.get('contract_list_sec')}"
    )
    info(f"[BotConfigLoader] Final config - exchanges: {[e.get('name') for e in config.get('exchanges', [])]}")
    info("[BotConfigLoader] Bot configuration validated successfully")

    # Add bot_accounts if available (needed for database collector initialization)
    if "bot_accounts" in bot_config:
        config["bot_accounts"] = bot_config["bot_accounts"]
        account_roles = list(config["bot_accounts"].keys())
        account_ids = [acc.get("id") for acc in config["bot_accounts"].values()]
        info(f"[BotConfigLoader] bot_accounts added to final config: roles={account_roles}, ids={account_ids}")
    else:
        warning("[BotConfigLoader] bot_accounts NOT found in bot_config - DatabaseCollector will not initialize!")

    return config


def transform_graph_bot_config(bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform graph arbitrage bot configuration from database format to runner format

    Args:
        bot_config: Configuration from database

    Returns:
        Transformed configuration for the graph runner
    """
    # Graph config should have a graph_config section
    if "graph_config" not in bot_config:
        raise ValueError("graph_arbitrage configuration must contain 'graph_config' section")

    graph_config: Dict[str, Any] = bot_config["graph_config"]

    # Validate exchanges in graph_config
    if "exchanges" not in graph_config or not isinstance(graph_config["exchanges"], list):
        raise ValueError("graph_config must contain 'exchanges' as a list")

    # Get parameters either from root or from parameters section
    parameters: Dict[str, Any] = bot_config.get("parameters", {})

    # Build the complete configuration with all fields the runner expects
    config: Dict[str, Any] = {
        # Bot metadata
        "bot_id": bot_config.get("bot_id"),
        "bot_name": bot_config.get("bot_name"),
        "strategy_type": "graph_arbitrage",
        # Copy the entire graph_config section
        "graph_config": graph_config,
        # Database configuration
        # Database connection details are in DATABASE_URL environment variable
        # DatabaseConfig.from_env() will parse DATABASE_URL to get all connection details
        "database": bot_config.get(
            "database",
            {
                "enabled": True,
                # Don't specify connection details here - DatabaseConfig.from_env() reads DATABASE_URL
            },
        ),
        # Threading configuration
        "threading": bot_config.get(
            "threading",
            {
                "use_threading": True,
                "position_recon_enabled": False,
            },
        ),
        # Parameter API configuration
        "parameter_api": bot_config.get("parameter_api", {"enabled": False}),
        # Add visualization if present
        "visualization": bot_config.get(
            "visualization",
            {
                "enabled": True,
                "update_interval_ms": 100,
                "show_top_opportunities": 10,
                "show_calculation_details": True,
                "show_price_comparison": True,
            },
        ),
    }

    # Check if parameters are in hierarchical format (has 'spread' group)
    if "spread" in parameters:
        # Hierarchical format - pass through as-is
        config["parameters"] = parameters
        info("[BotConfigLoader] Graph bot using hierarchical parameter format")
    else:
        # Flat format - should not happen with new system
        raise ValueError(
            "Graph bot configuration uses deprecated flat parameter format. "
            "Please update to hierarchical format with 'spread', 'sizing' groups."
        )

    # Add bot_accounts if available
    if "bot_accounts" in bot_config:
        config["bot_accounts"] = bot_config["bot_accounts"]

        # Hub-only order submission uses websocket command semantics by design.
        use_websocket_for_orders_graph = True

        # Update each exchange in graph_config with credentials if available
        for exchange in graph_config["exchanges"]:
            exchange_id: str = exchange.get("id", "").lower()

            # Check if we have an account for this exchange
            # Both sides are canonical ExchangeName values — exact match only
            for _role, account in bot_config.get("bot_accounts", {}).items():
                if account["exchange"].lower() == exchange_id:
                    # Add credential reference to the exchange config
                    exchange["account_id"] = account.get("id")
                    exchange["credential_ref"] = account["credential_ref"]
                    exchange["credential_storage_type"] = account.get("credential_storage_type", "reference")
                    exchange["is_testnet"] = account.get("is_testnet", False)
                    exchange["account_type"] = account.get("account_type", "futures")
                    break

            # Add WebSocket preference
            if "use_websocket_for_orders" not in exchange:
                exchange["use_websocket_for_orders"] = use_websocket_for_orders_graph

    # Add other configuration sections if present (same as cross_arb transform)
    if "risk_management" in bot_config:
        config["risk_management"] = bot_config["risk_management"]
        info("[BotConfigLoader] Added risk_management config to graph bot")

    if "unwinder" in bot_config:
        config["unwinder"] = bot_config["unwinder"]
        info(f"[BotConfigLoader] Added unwinder config to graph bot: {bot_config['unwinder']}")

    if "monitoring" in bot_config:
        config["monitoring"] = bot_config["monitoring"]
        info("[BotConfigLoader] Added monitoring config to graph bot")

    if "data_sources" in bot_config:
        config["data_sources"] = bot_config["data_sources"]

    # Validate required fields
    required_fields: List[str] = [
        "bot_id",
        "bot_name",
        "strategy_type",
        "graph_config",
        "parameters",  # Hierarchical parameters
    ]

    missing_fields: List[str] = []
    for field in required_fields:
        if field not in config or config[field] is None:
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(f"Missing required fields in graph bot configuration: {', '.join(missing_fields)}")

    # Validate hierarchical parameters have required groups
    params = config.get("parameters", {})
    if "spread" not in params:
        raise ValueError("Missing required 'spread' group in graph bot parameters")
    if "sizing" not in params:
        raise ValueError("Missing required 'sizing' group in graph bot parameters")

    info("[BotConfigLoader] Graph bot configuration validated successfully")

    return config
