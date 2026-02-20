"""Bot configuration models with Pydantic validation.

This module provides validated configuration models for bot operation,
replacing the previous TypedDict-based configuration with runtime validation.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from data_models.models.enums.exchange import ExchangeName

# Valid exchange names derived from ExchangeName enum
EXCHANGE_NAMES = [e.value for e in ExchangeName]


class ExchangeConfig(BaseModel):
    """Exchange role configuration for arbitrage."""

    model_config = ConfigDict(extra="forbid")

    maker: str = Field(..., min_length=1, description="Maker exchange name")
    taker: str = Field(..., min_length=1, description="Taker exchange name")

    @field_validator("maker", "taker")
    @classmethod
    def validate_exchange_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Exchange name cannot be empty")
        return v


class ParametersConfig(BaseModel):
    """Trading parameters configuration with validation.

    All spread/percentage parameters are in percentage format where:
    - 0.20 = 0.20% = 20 basis points
    - 1.00 = 1.00% = 100 basis points
    """

    model_config = ConfigDict(extra="forbid")

    target_premium: float = Field(..., ge=0.0, description="Target spread in %")
    target_discount: float = Field(..., ge=0.0, description="Target spread in %")
    taker_spread: float = Field(..., ge=0.0, description="Taker fee adjustment in %")
    max_target_deviation: float = Field(..., ge=0.0, description="Max price deviation in %")
    accepted_slippage: float = Field(..., ge=0.0, description="Accepted slippage in %")
    is_dollar_amt: bool
    maximum_amount_premium: float = Field(..., ge=0.0)
    maximum_amount_discount: float = Field(..., ge=0.0)
    trade_amt_cap: float = Field(..., gt=0.0)
    trade_amt_floor: float = Field(..., gt=0.0)
    min_dist_maker: int = Field(..., ge=0)
    wait_for_taker_fill: bool = Field(..., description="Wait for taker order to fill completely before processing execution")
    taker_latency_timeout: int = Field(..., gt=0, description="Timeout in milliseconds for taker order execution")
    maker_staleness_threshold_ms: int = Field(
        default=2000, ge=100, le=30000, description="Maximum age in ms for maker orderbook before considered stale"
    )
    taker_staleness_threshold_ms: int = Field(
        default=2000, ge=100, le=30000, description="Maximum age in ms for taker orderbook before considered stale"
    )
    is_graph_latency: bool = False
    log_level: str = "INFO"


class DatabaseConfig(BaseModel):
    """Database configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    host: str = Field(..., min_length=1)
    port: int = Field(..., gt=0, le=65535)
    database: str = Field(..., min_length=1)
    user: str = Field(..., min_length=1)
    password: str
    min_connections: Optional[int] = Field(None, ge=1)
    max_connections: Optional[int] = Field(None, ge=1)


class ThreadingConfig(BaseModel):
    """Threading configuration."""

    model_config = ConfigDict(extra="forbid")

    message_handler_threaded: bool
    bot_threaded: bool
    disable_trading_loop: bool


class LiveTestingConfig(BaseModel):
    """Live testing configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    exchange: bool
    cancel_maker: bool
    cancel_inverted: bool
    execution: bool


class MonitorsConfig(BaseModel):
    """Monitors configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool


class BotAccountConfig(BaseModel):
    """Bot account assignment configuration."""

    model_config = ConfigDict(extra="forbid")

    maker_account_id: Optional[int] = Field(None, ge=1, description="Account ID for maker exchange")
    taker_account_id: Optional[int] = Field(None, ge=1, description="Account ID for taker exchange")


class PositionLimitsConfig(BaseModel):
    """Position limits configuration."""

    model_config = ConfigDict(extra="forbid")

    max_position_size_usd: Optional[float] = Field(None, gt=0.0)
    max_position_per_pair: Optional[float] = Field(None, gt=0.0)
    max_total_exposure: Optional[float] = Field(None, gt=0.0)
    position_check_interval_ms: Optional[int] = Field(None, gt=0)


class RiskManagementConfig(BaseModel):
    """Risk management configuration."""

    model_config = ConfigDict(extra="forbid")

    max_position_size_usd: Optional[float] = Field(None, gt=0.0)
    max_daily_loss_usd: Optional[float] = Field(None, gt=0.0)
    max_drawdown_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    emergency_stop_enabled: Optional[bool] = None
    stop_loss_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    take_profit_percentage: Optional[float] = Field(None, ge=0.0)


class BotConfigDB(BaseModel):
    """Bot configuration as stored in database."""

    model_config = ConfigDict(extra="forbid")

    exchanges: ExchangeConfig
    contract_list_main: List[str] = Field(..., min_length=1)
    contract_list_sec: List[str] = Field(..., min_length=1)
    parameters: ParametersConfig
    env_vars: Optional[Dict[str, str]] = None
    bot_accounts: Optional[BotAccountConfig] = None
    database: Optional[DatabaseConfig] = None
    position_limits: Optional[PositionLimitsConfig] = None
    risk_management: Optional[RiskManagementConfig] = None

    @field_validator("contract_list_main", "contract_list_sec")
    @classmethod
    def validate_contracts(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Contract list cannot be empty")

        for i, contract in enumerate(v):
            if not contract or not contract.strip():
                raise ValueError(f"Contract[{i}] cannot be empty")

            if contract.lower() in EXCHANGE_NAMES:
                raise ValueError(
                    f"Invalid contract {contract!r} - appears to be an exchange name. "
                    "Expected format like 'BTC_USDC', 'ETH_USDC', or 'HYPE_USD'"
                )

        return v


class ExchangeConfigRunner(BaseModel):
    """Exchange configuration for runner."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    credential_ref: Optional[str] = None
    is_testnet: bool = False
    use_websocket_for_orders: bool = False
    passphrase: Optional[str] = None


class StrategyConfig(BaseModel):
    """Base configuration for market-making strategies."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    priority: Optional[int] = Field(None, ge=0)


class GraphExchangeConfig(BaseModel):
    """Configuration for an exchange in graph arbitrage."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, description="Exchange identifier")
    contracts: List[str] = Field(..., min_length=1)
    account_id: Optional[int] = Field(None, ge=1)
    is_testnet: bool = False


class GraphStrategyConfig(StrategyConfig):
    """Configuration for graph-based market-making strategy."""

    max_concurrent_paths: Optional[int] = Field(None, ge=1)
    min_spread_threshold: Optional[float] = Field(None, ge=0.0)
    path_types: Optional[List[str]] = None
    refresh_interval_ms: Optional[int] = Field(None, gt=0)
    exchanges: Optional[List[GraphExchangeConfig]] = None
    pairs: Optional[List[str]] = None
    max_path_length: int = Field(2, ge=1, le=10)
    enable_cross_pair: bool = False


class BotConfigRunner(BaseModel):
    """Bot configuration for runner after transformation."""

    model_config = ConfigDict(extra="forbid")

    bot_id: int = Field(..., ge=1)
    bot_name: str = Field(..., min_length=1)
    strategy_type: str = Field(..., min_length=1)

    exchanges: List[ExchangeConfigRunner] = Field(..., min_length=1)

    contract_list_main: List[str] = Field(..., min_length=1)
    contract_list_sec: List[str] = Field(..., min_length=1)
    routing_list: List[str] = Field(..., min_length=1)

    database: DatabaseConfig
    threading: ThreadingConfig
    live_testing: LiveTestingConfig
    monitors: MonitorsConfig

    target_premium: float = Field(..., ge=0.0)
    target_discount: float = Field(..., ge=0.0)
    taker_spread: float = Field(..., ge=0.0)
    max_target_deviation: float = Field(..., ge=0.0)
    accepted_slippage: float = Field(..., ge=0.0)
    is_dollar_amt: bool
    maximum_amount_premium: float = Field(..., ge=0.0)
    maximum_amount_discount: float = Field(..., ge=0.0)
    trade_amt_cap: float = Field(..., gt=0.0)
    trade_amt_floor: float = Field(..., gt=0.0)
    min_dist_maker: int = Field(..., ge=0)
    wait_for_taker_fill: bool = Field(..., description="Wait for taker order to fill completely before processing execution")
    taker_latency_timeout: int = Field(..., gt=0, description="Timeout in milliseconds for taker order execution")
    maker_staleness_threshold_ms: int = Field(
        default=2000, ge=100, le=30000, description="Maximum age in ms for maker orderbook before considered stale"
    )
    taker_staleness_threshold_ms: int = Field(
        default=2000, ge=100, le=30000, description="Maximum age in ms for taker orderbook before considered stale"
    )
    is_graph_latency: bool
    log_level: str

    position_limits: Optional[PositionLimitsConfig] = None
    risk_management: Optional[RiskManagementConfig] = None
    graph_config: Optional[GraphStrategyConfig] = None
