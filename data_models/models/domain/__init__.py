"""
Domain models package.

Core business entities organized by subdomain:
    - order/: Order, OrderRequest, order ID types
    - market/: Orderbook, Ticker, Quote, Trade
    - account/: Balance, Position, futures data
    - trading/: TradingPair, LiquidateInstructions, latency
    - gateway/: GatewayHealthSnapshot for health monitoring

Import directly from specific modules:
    from data_models.models.domain.order.order import Order
    from data_models.models.domain.market.orderbook import Orderbook
    from data_models.models.domain.account.position import Position
    from data_models.models.domain.gateway.health import GatewayHealthSnapshot
"""
