"""
Models package for Helena Bot.

This package contains all model definitions organized by concern.
Import directly from the specific modules:

    from data_models.models.enums.order import OrderSide, OrderStatus, OrderType
    from data_models.models.enums.trading import BotState, TradeSide, RoutingType
    from data_models.models.domain.order.order import Order
    from data_models.models.domain.market.orderbook import Orderbook
    from data_models.models.domain.account.position import Position
    from data_models.models.domain.account.balance import Balance
    from data_models.models.domain.trading.contract import Contract, ensure_contract
    from data_models.models.config.bot import BotConfigRunner
    from data_models.models.exceptions import ModelError
    from data_models.models.runtime_control_plane import RuntimeHealthReportContract

Package structure:
    - enums/: All enum definitions (OrderSide, BotState, etc.)
    - domain/: Core business entities organized by subdomain
        - order/: Order, OrderRequest, order IDs
        - market/: Orderbook, Ticker, Quote, Trade
        - account/: Balance, Position, futures data
        - trading/: Contract, TradingPair, LiquidateInstructions, latency
    - exchange/: Exchange-specific API response models
    - engine/: Engine layer models (ExecutionContext, etc.)
    - broker/: Broker layer models (cache, stats)
    - config/: Configuration models
    - protocols/: Protocol definitions
"""
