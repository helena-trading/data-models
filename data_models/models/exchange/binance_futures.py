"""
Binance Futures API Response Models

Typed models for Binance Futures API responses to replace Dict[str, Any] usage.
These models provide type safety and better IDE support while maintaining compatibility
with the V1 implementation field names and types.
"""

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field


# Enums for type safety
class OrderType(str, Enum):
    """Binance Futures order types."""

    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"


class OrderSide(str, Enum):
    """Order sides."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """Binance Futures order statuses."""

    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    EXPIRED_IN_MATCH = "EXPIRED_IN_MATCH"


class TimeInForce(str, Enum):
    """Time in force options."""

    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill
    GTX = "GTX"  # Good Till Crossing (Post Only)


class PositionSide(str, Enum):
    """Position sides for hedge mode."""

    BOTH = "BOTH"
    LONG = "LONG"
    SHORT = "SHORT"


class MarginType(str, Enum):
    """Margin types."""

    CROSS = "cross"
    ISOLATED = "isolated"


class WorkingType(str, Enum):
    """Working price types."""

    MARK_PRICE = "MARK_PRICE"
    CONTRACT_PRICE = "CONTRACT_PRICE"


class ContractType(str, Enum):
    """Contract types."""

    PERPETUAL = "PERPETUAL"
    CURRENT_MONTH = "CURRENT_MONTH"
    NEXT_MONTH = "NEXT_MONTH"
    CURRENT_QUARTER = "CURRENT_QUARTER"
    NEXT_QUARTER = "NEXT_QUARTER"


class SymbolStatus(str, Enum):
    """Symbol trading status."""

    TRADING = "TRADING"
    PRE_TRADING = "PRE_TRADING"
    POST_TRADING = "POST_TRADING"
    END_OF_DAY = "END_OF_DAY"
    HALT = "HALT"
    AUCTION_MATCH = "AUCTION_MATCH"
    BREAK = "BREAK"


# Core response models
class BinanceFuturesOrderResponse(BaseModel):
    """
    Binance Futures order response model.

    Used for both REST order creation responses and order query responses.
    Maintains exact field names from V1 implementation for compatibility.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    orderId: int = Field(..., description="Unique order ID assigned by exchange")
    symbol: str = Field(..., description='Exchange symbol format (e.g., "BTCUSDT")')
    status: str = Field(..., description="Order status")
    clientOrderId: str = Field(..., description="Client-provided order ID")
    price: str = Field(..., description="Order price (0 for market orders)")
    avgPrice: str = Field(..., description="Average execution price")
    origQty: str = Field(..., description="Original order quantity")
    executedQty: str = Field(..., description="Quantity already executed")
    cumQty: str = Field(..., description="Cumulative filled quantity (alias for executedQty)")
    cumQuote: str = Field(..., description="Cumulative quote asset transacted quantity")
    timeInForce: str = Field(..., description="Time in force")
    type: str = Field(..., description="Order type")
    reduceOnly: bool = Field(..., description="Reduce only flag")
    closePosition: bool = Field(..., description="Close position flag")
    side: str = Field(..., description="Order side (BUY/SELL)")
    positionSide: str = Field(..., description="Position side (BOTH/LONG/SHORT)")
    stopPrice: str = Field(..., description="Stop price")
    workingType: str = Field(..., description="Working price type")
    priceProtect: bool = Field(..., description="Price protection")
    origType: str = Field(..., description="Original order type")
    time: int = Field(..., description="Order creation timestamp")
    updateTime: int = Field(..., description="Last update timestamp")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesOrderResponse":
        """Create from API response dict."""
        return cls(
            orderId=data.get("orderId", 0),
            symbol=data.get("symbol", ""),
            status=data.get("status", ""),
            clientOrderId=data.get("clientOrderId", ""),
            price=data.get("price", "0"),
            avgPrice=data.get("avgPrice", "0"),
            origQty=data.get("origQty", "0"),
            executedQty=data.get("executedQty", "0"),
            cumQty=data.get("cumQty", data.get("executedQty", "0")),
            cumQuote=data.get("cumQuote", "0"),
            timeInForce=data.get("timeInForce", "GTC"),
            type=data.get("type", "LIMIT"),
            reduceOnly=data.get("reduceOnly", False),
            closePosition=data.get("closePosition", False),
            side=data.get("side", "BUY"),
            positionSide=data.get("positionSide", "BOTH"),
            stopPrice=data.get("stopPrice", "0"),
            workingType=data.get("workingType", "CONTRACT_PRICE"),
            priceProtect=data.get("priceProtect", False),
            origType=data.get("origType", "LIMIT"),
            time=data.get("time", 0),
            updateTime=data.get("updateTime", 0),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == "FILLED"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in ["NEW", "PARTIALLY_FILLED"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_buy_order(self) -> bool:
        """Check if this is a buy order."""
        return self.side == "BUY"

    def get_price_decimal(self) -> Decimal:
        """Get price as Decimal for precision calculations."""
        return Decimal(self.price) if self.price else Decimal("0")

    def get_avg_price_decimal(self) -> Decimal:
        """Get average price as Decimal."""
        return Decimal(self.avgPrice) if self.avgPrice else Decimal("0")

    def get_quantity_decimal(self) -> Decimal:
        """Get original quantity as Decimal."""
        return Decimal(self.origQty) if self.origQty else Decimal("0")

    def get_executed_qty_decimal(self) -> Decimal:
        """Get executed quantity as Decimal."""
        return Decimal(self.executedQty) if self.executedQty else Decimal("0")


class BinanceFuturesPosition(BaseModel):
    """
    Binance Futures position information.

    Maintains exact field names from V1 implementation for compatibility.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., description="Trading symbol")
    positionAmt: str = Field(..., description="Position amount (negative for short)")
    entryPrice: str = Field(..., description="Average entry price")
    markPrice: str = Field(..., description="Current mark price")
    unRealizedProfit: str = Field(..., description="Unrealized PnL")
    liquidationPrice: str = Field(..., description="Liquidation price")
    leverage: str = Field(..., description="Current leverage")
    maxNotionalValue: str = Field(..., description="Maximum notional value")
    marginType: str = Field(..., description="Margin type (cross/isolated)")
    isolatedMargin: str = Field(..., description="Isolated margin")
    isAutoAddMargin: str = Field(..., description="Auto add margin flag")
    positionSide: str = Field(..., description="Position side (BOTH/LONG/SHORT)")
    notional: str = Field(..., description="Notional value")
    isolatedWallet: str = Field(..., description="Isolated wallet balance")
    updateTime: int = Field(..., description="Last update timestamp")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesPosition":
        """Create from API response dict."""
        return cls(
            symbol=data.get("symbol", ""),
            positionAmt=data.get("positionAmt", "0"),
            entryPrice=data.get("entryPrice", "0"),
            markPrice=data.get("markPrice", "0"),
            unRealizedProfit=data.get("unRealizedProfit", "0"),
            liquidationPrice=data.get("liquidationPrice", "0"),
            leverage=data.get("leverage", "0"),
            maxNotionalValue=data.get("maxNotionalValue", "0"),
            marginType=data.get("marginType", "cross"),
            isolatedMargin=data.get("isolatedMargin", "0"),
            isAutoAddMargin=data.get("isAutoAddMargin", "false"),
            positionSide=data.get("positionSide", "BOTH"),
            notional=data.get("notional", "0"),
            isolatedWallet=data.get("isolatedWallet", "0"),
            updateTime=data.get("updateTime", 0),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_position(self) -> bool:
        """Check if there's an actual position (size != 0)."""
        return self.get_position_amt_decimal() != Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_long_position(self) -> bool:
        """Check if this is a long position."""
        return self.get_position_amt_decimal() > Decimal("0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_short_position(self) -> bool:
        """Check if this is a short position."""
        return self.get_position_amt_decimal() < Decimal("0")

    def get_position_amt_decimal(self) -> Decimal:
        """Get position amount as Decimal."""
        return Decimal(self.positionAmt) if self.positionAmt else Decimal("0")

    def get_entry_price_decimal(self) -> Decimal:
        """Get entry price as Decimal."""
        return Decimal(self.entryPrice) if self.entryPrice else Decimal("0")

    def get_mark_price_decimal(self) -> Decimal:
        """Get mark price as Decimal."""
        return Decimal(self.markPrice) if self.markPrice else Decimal("0")

    def get_unrealized_pnl_decimal(self) -> Decimal:
        """Get unrealized PnL as Decimal."""
        return Decimal(self.unRealizedProfit) if self.unRealizedProfit else Decimal("0")

    def get_liquidation_price_decimal(self) -> Decimal:
        """Get liquidation price as Decimal."""
        return Decimal(self.liquidationPrice) if self.liquidationPrice else Decimal("0")


class BinanceFuturesFundingRate(BaseModel):
    """Binance Futures funding rate information."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., description="Trading symbol")
    fundingRate: str = Field(..., description="Current funding rate")
    fundingTime: int = Field(..., description="Funding timestamp")
    markPrice: Optional[str] = Field(None, description="Mark price at funding time")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesFundingRate":
        """Create from API response dict.

        Binance API returns:
        - lastFundingRate: The most recent funding rate
        - nextFundingTime: Timestamp of next funding settlement
        """
        return cls(
            symbol=data.get("symbol", ""),
            # API returns "lastFundingRate" not "fundingRate"
            fundingRate=data.get("lastFundingRate", data.get("fundingRate", "0")),
            # API returns "nextFundingTime" not "fundingTime"
            fundingTime=data.get("nextFundingTime", data.get("fundingTime", 0)),
            markPrice=data.get("markPrice"),
        )

    def get_funding_rate_decimal(self) -> Decimal:
        """Get funding rate as Decimal."""
        return Decimal(self.fundingRate) if self.fundingRate else Decimal("0")

    def get_mark_price_decimal(self) -> Optional[Decimal]:
        """Get mark price as Decimal."""
        return Decimal(self.markPrice) if self.markPrice else None


class BinanceFuturesAccountBalance(BaseModel):
    """Binance Futures account balance for a single asset."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    asset: str = Field(..., description='Asset symbol (e.g., "USDT")')
    walletBalance: str = Field(..., description="Wallet balance")
    unrealizedProfit: str = Field(..., description="Unrealized PnL")
    marginBalance: str = Field(..., description="Margin balance")
    maintMargin: str = Field(..., description="Maintenance margin")
    initialMargin: str = Field(..., description="Initial margin")
    positionInitialMargin: str = Field(..., description="Position initial margin")
    openOrderInitialMargin: str = Field(..., description="Open order initial margin")
    crossWalletBalance: str = Field(..., description="Cross wallet balance")
    crossUnPnl: str = Field(..., description="Cross unrealized PnL")
    availableBalance: str = Field(..., description="Available balance")
    maxWithdrawAmount: str = Field(..., description="Maximum withdraw amount")
    marginAvailable: Optional[bool] = Field(None, description="Margin available flag")
    updateTime: Optional[int] = Field(None, description="Update timestamp")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesAccountBalance":
        """Create from API response dict."""
        return cls(
            asset=data.get("asset", ""),
            walletBalance=data.get("walletBalance", "0"),
            unrealizedProfit=data.get("unrealizedProfit", "0"),
            marginBalance=data.get("marginBalance", "0"),
            maintMargin=data.get("maintMargin", "0"),
            initialMargin=data.get("initialMargin", "0"),
            positionInitialMargin=data.get("positionInitialMargin", "0"),
            openOrderInitialMargin=data.get("openOrderInitialMargin", "0"),
            crossWalletBalance=data.get("crossWalletBalance", "0"),
            crossUnPnl=data.get("crossUnPnl", "0"),
            availableBalance=data.get("availableBalance", "0"),
            maxWithdrawAmount=data.get("maxWithdrawAmount", "0"),
            marginAvailable=data.get("marginAvailable"),
            updateTime=data.get("updateTime"),
        )

    def get_wallet_balance_decimal(self) -> Decimal:
        """Get wallet balance as Decimal."""
        return Decimal(self.walletBalance) if self.walletBalance else Decimal("0")

    def get_available_balance_decimal(self) -> Decimal:
        """Get available balance as Decimal."""
        return Decimal(self.availableBalance) if self.availableBalance else Decimal("0")

    def get_unrealized_profit_decimal(self) -> Decimal:
        """Get unrealized profit as Decimal."""
        return Decimal(self.unrealizedProfit) if self.unrealizedProfit else Decimal("0")

    def get_margin_balance_decimal(self) -> Decimal:
        """Get margin balance as Decimal."""
        return Decimal(self.marginBalance) if self.marginBalance else Decimal("0")


class BinanceFuturesAccountInfo(BaseModel):
    """Binance Futures account information."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    feeTier: int = Field(..., description="Fee tier level")
    canTrade: bool = Field(..., description="Can place orders")
    canDeposit: bool = Field(..., description="Can deposit")
    canWithdraw: bool = Field(..., description="Can withdraw")
    updateTime: int = Field(..., description="Last account update timestamp")
    totalInitialMargin: str = Field(..., description="Total initial margin")
    totalMaintMargin: str = Field(..., description="Total maintenance margin")
    totalWalletBalance: str = Field(..., description="Total wallet balance")
    totalUnrealizedProfit: str = Field(..., description="Total unrealized profit")
    totalMarginBalance: str = Field(..., description="Total margin balance")
    totalPositionInitialMargin: str = Field(..., description="Total position initial margin")
    totalOpenOrderInitialMargin: str = Field(..., description="Total open order initial margin")
    totalCrossWalletBalance: str = Field(..., description="Total cross wallet balance")
    totalCrossUnPnl: str = Field(..., description="Total cross unrealized PnL")
    availableBalance: str = Field(..., description="Available balance")
    maxWithdrawAmount: str = Field(..., description="Maximum withdraw amount")
    assets: List[Dict[str, Any]] = Field(..., description="Asset balances (raw data)")
    positions: List[Dict[str, Any]] = Field(..., description="Position data (raw data)")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesAccountInfo":
        """Create from API response dict."""
        return cls(
            feeTier=data.get("feeTier", 0),
            canTrade=data.get("canTrade", False),
            canDeposit=data.get("canDeposit", False),
            canWithdraw=data.get("canWithdraw", False),
            updateTime=data.get("updateTime", 0),
            totalInitialMargin=data.get("totalInitialMargin", "0"),
            totalMaintMargin=data.get("totalMaintMargin", "0"),
            totalWalletBalance=data.get("totalWalletBalance", "0"),
            totalUnrealizedProfit=data.get("totalUnrealizedProfit", "0"),
            totalMarginBalance=data.get("totalMarginBalance", "0"),
            totalPositionInitialMargin=data.get("totalPositionInitialMargin", "0"),
            totalOpenOrderInitialMargin=data.get("totalOpenOrderInitialMargin", "0"),
            totalCrossWalletBalance=data.get("totalCrossWalletBalance", "0"),
            totalCrossUnPnl=data.get("totalCrossUnPnl", "0"),
            availableBalance=data.get("availableBalance", "0"),
            maxWithdrawAmount=data.get("maxWithdrawAmount", "0"),
            assets=data.get("assets", []),
            positions=data.get("positions", []),
        )

    def get_balances(self) -> List[BinanceFuturesAccountBalance]:
        """Get typed balance objects."""
        return [BinanceFuturesAccountBalance.from_dict(asset) for asset in self.assets]

    def get_positions(self) -> List[BinanceFuturesPosition]:
        """Get typed position objects."""
        return [BinanceFuturesPosition.from_dict(pos) for pos in self.positions]

    def get_balance(self, asset: str) -> Optional[BinanceFuturesAccountBalance]:
        """Get balance for specific asset."""
        for asset_data in self.assets:
            if asset_data.get("asset") == asset:
                return BinanceFuturesAccountBalance.from_dict(asset_data)
        return None


class BinanceFuturesLeverageInfo(BaseModel):
    """Leverage bracket information."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    bracket: int = Field(..., description="Bracket level")
    initialLeverage: int = Field(..., description="Maximum leverage")
    notionalCap: str = Field(..., description="Notional cap for this bracket")
    notionalFloor: str = Field(..., description="Notional floor for this bracket")
    maintMarginRatio: str = Field(..., description="Maintenance margin ratio")
    cum: str = Field(..., description="Cumulative amount")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesLeverageInfo":
        """Create from API response dict."""
        return cls(
            bracket=data.get("bracket", 0),
            initialLeverage=data.get("initialLeverage", 0),
            notionalCap=data.get("notionalCap", "0"),
            notionalFloor=data.get("notionalFloor", "0"),
            maintMarginRatio=data.get("maintMarginRatio", "0"),
            cum=data.get("cum", "0"),
        )


class BinanceFuturesSymbolInfo(BaseModel):
    """
    Trading rules and information for a Binance Futures symbol.

    Part of exchange info response.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., description="Trading pair symbol")
    pair: str = Field(..., description="Underlying pair")
    contractType: str = Field(..., description="Contract type")
    deliveryDate: int = Field(..., description="Delivery date timestamp")
    onboardDate: int = Field(..., description="Onboard date timestamp")
    status: str = Field(..., description="Trading status")
    maintMarginPercent: str = Field(..., description="Maintenance margin percentage")
    requiredMarginPercent: str = Field(..., description="Required margin percentage")
    baseAsset: str = Field(..., description="Base asset")
    quoteAsset: str = Field(..., description="Quote asset")
    marginAsset: str = Field(..., description="Margin asset")
    pricePrecision: int = Field(..., description="Price precision")
    quantityPrecision: int = Field(..., description="Quantity precision")
    baseAssetPrecision: int = Field(..., description="Base asset precision")
    quotePrecision: int = Field(..., description="Quote precision")
    underlyingType: str = Field(..., description="Underlying type")
    underlyingSubType: List[str] = Field(..., description="Underlying sub types")
    settlePlan: int = Field(..., description="Settlement plan")
    triggerProtect: str = Field(..., description="Trigger protection threshold")
    liquidationFee: str = Field(..., description="Liquidation fee rate")
    marketTakeBound: str = Field(..., description="Market take bound")
    filters: List[Dict[str, Any]] = Field(..., description="Price, quantity, and other filters")
    orderTypes: Optional[List[str]] = Field(None, description="Allowed order types")
    timeInForce: Optional[List[str]] = Field(None, description="Allowed time in force values")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesSymbolInfo":
        """Create from API response dict."""
        return cls(
            symbol=data.get("symbol", ""),
            pair=data.get("pair", ""),
            contractType=data.get("contractType", ""),
            deliveryDate=data.get("deliveryDate", 0),
            onboardDate=data.get("onboardDate", 0),
            status=data.get("status", ""),
            maintMarginPercent=data.get("maintMarginPercent", "0"),
            requiredMarginPercent=data.get("requiredMarginPercent", "0"),
            baseAsset=data.get("baseAsset", ""),
            quoteAsset=data.get("quoteAsset", ""),
            marginAsset=data.get("marginAsset", ""),
            pricePrecision=data.get("pricePrecision", 0),
            quantityPrecision=data.get("quantityPrecision", 0),
            baseAssetPrecision=data.get("baseAssetPrecision", 0),
            quotePrecision=data.get("quotePrecision", 0),
            underlyingType=data.get("underlyingType", ""),
            underlyingSubType=data.get("underlyingSubType", []),
            settlePlan=data.get("settlePlan", 0),
            triggerProtect=data.get("triggerProtect", "0"),
            liquidationFee=data.get("liquidationFee", "0"),
            marketTakeBound=data.get("marketTakeBound", "0"),
            filters=data.get("filters", []),
            orderTypes=data.get("orderTypes"),
            timeInForce=data.get("timeInForce"),
        )

    def get_price_filter(self) -> Optional[Dict[str, Any]]:
        """Get price filter rules."""
        for f in self.filters:
            if f.get("filterType") == "PRICE_FILTER":
                return f
        return None

    def get_lot_size_filter(self) -> Optional[Dict[str, Any]]:
        """Get lot size (quantity) filter rules."""
        for f in self.filters:
            if f.get("filterType") == "LOT_SIZE":
                return f
        return None

    def get_market_lot_size_filter(self) -> Optional[Dict[str, Any]]:
        """Get market lot size filter rules."""
        for f in self.filters:
            if f.get("filterType") == "MARKET_LOT_SIZE":
                return f
        return None

    def get_max_num_orders_filter(self) -> Optional[Dict[str, Any]]:
        """Get maximum number of orders filter."""
        for f in self.filters:
            if f.get("filterType") == "MAX_NUM_ORDERS":
                return f
        return None

    def get_percent_price_filter(self) -> Optional[Dict[str, Any]]:
        """Get percent price filter rules."""
        for f in self.filters:
            if f.get("filterType") == "PERCENT_PRICE":
                return f
        return None


class BinanceFuturesExchangeInfo(BaseModel):
    """Binance Futures exchange information."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    timezone: str = Field(..., description="Exchange timezone")
    serverTime: int = Field(..., description="Server timestamp")
    futuresType: str = Field(..., description="Futures type (U_MARGINED/COIN_MARGINED)")
    rateLimits: List[Dict[str, Any]] = Field(..., description="Rate limit rules")
    exchangeFilters: List[Dict[str, Any]] = Field(..., description="Exchange-level filters")
    assets: List[Dict[str, Any]] = Field(..., description="Available assets")
    symbols: List[Dict[str, Any]] = Field(..., description="Trading symbols (raw data)")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesExchangeInfo":
        """Create from API response dict."""
        return cls(
            timezone=data.get("timezone", "UTC"),
            serverTime=data.get("serverTime", 0),
            futuresType=data.get("futuresType", "U_MARGINED"),
            rateLimits=data.get("rateLimits", []),
            exchangeFilters=data.get("exchangeFilters", []),
            assets=data.get("assets", []),
            symbols=data.get("symbols", []),
        )

    def get_symbols(self) -> List[BinanceFuturesSymbolInfo]:
        """Get typed symbol objects."""
        return [BinanceFuturesSymbolInfo.from_dict(symbol) for symbol in self.symbols]

    def get_symbol(self, symbol: str) -> Optional[BinanceFuturesSymbolInfo]:
        """Get symbol info by name."""
        for symbol_data in self.symbols:
            if symbol_data.get("symbol") == symbol:
                return BinanceFuturesSymbolInfo.from_dict(symbol_data)
        return None


# Market Data Models
class BinanceFuturesOrderbookResponse(BaseModel):
    """Binance Futures orderbook (depth) response."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    lastUpdateId: int = Field(..., description="Last update ID")
    E: int = Field(..., description="Message output timestamp")
    T: int = Field(..., description="Transaction timestamp")
    bids: List[List[str]] = Field(..., description="[[price, quantity], ...]")
    asks: List[List[str]] = Field(..., description="[[price, quantity], ...]")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesOrderbookResponse":
        """Create from API response dict."""
        return cls(
            lastUpdateId=data.get("lastUpdateId", 0),
            E=data.get("E", 0),
            T=data.get("T", 0),
            bids=data.get("bids", []),
            asks=data.get("asks", []),
        )

    def get_best_bid_price(self) -> Optional[Decimal]:
        """Get best bid price as Decimal."""
        if self.bids and len(self.bids) > 0:
            return Decimal(self.bids[0][0])
        return None

    def get_best_ask_price(self) -> Optional[Decimal]:
        """Get best ask price as Decimal."""
        if self.asks and len(self.asks) > 0:
            return Decimal(self.asks[0][0])
        return None

    def get_best_bid_size(self) -> Optional[Decimal]:
        """Get best bid size as Decimal."""
        if self.bids and len(self.bids) > 0:
            return Decimal(self.bids[0][1])
        return None

    def get_best_ask_size(self) -> Optional[Decimal]:
        """Get best ask size as Decimal."""
        if self.asks and len(self.asks) > 0:
            return Decimal(self.asks[0][1])
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate spread between best bid and ask."""
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None


class BinanceFuturesTickerResponse(BaseModel):
    """Binance Futures 24hr ticker statistics."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., description="Symbol name")
    priceChange: str = Field(..., description="Price change")
    priceChangePercent: str = Field(..., description="Price change percent")
    weightedAvgPrice: str = Field(..., description="Weighted average price")
    lastPrice: str = Field(..., description="Last price")
    lastQty: str = Field(..., description="Last quantity")
    openPrice: str = Field(..., description="Open price")
    highPrice: str = Field(..., description="High price")
    lowPrice: str = Field(..., description="Low price")
    volume: str = Field(..., description="Volume")
    quoteVolume: str = Field(..., description="Quote asset volume")
    openTime: int = Field(..., description="Open time")
    closeTime: int = Field(..., description="Close time")
    firstId: int = Field(..., description="First trade ID")
    lastId: int = Field(..., description="Last trade ID")
    count: int = Field(..., description="Trade count")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesTickerResponse":
        """Create from API response dict."""
        return cls(
            symbol=data.get("symbol", ""),
            priceChange=data.get("priceChange", "0"),
            priceChangePercent=data.get("priceChangePercent", "0"),
            weightedAvgPrice=data.get("weightedAvgPrice", "0"),
            lastPrice=data.get("lastPrice", "0"),
            lastQty=data.get("lastQty", "0"),
            openPrice=data.get("openPrice", "0"),
            highPrice=data.get("highPrice", "0"),
            lowPrice=data.get("lowPrice", "0"),
            volume=data.get("volume", "0"),
            quoteVolume=data.get("quoteVolume", "0"),
            openTime=data.get("openTime", 0),
            closeTime=data.get("closeTime", 0),
            firstId=data.get("firstId", 0),
            lastId=data.get("lastId", 0),
            count=data.get("count", 0),
        )

    def get_last_price_decimal(self) -> Decimal:
        """Get last price as Decimal."""
        return Decimal(self.lastPrice) if self.lastPrice else Decimal("0")

    def get_price_change_percent_decimal(self) -> Decimal:
        """Get price change percentage as Decimal."""
        return Decimal(self.priceChangePercent) if self.priceChangePercent else Decimal("0")

    def get_volume_decimal(self) -> Decimal:
        """Get volume as Decimal."""
        return Decimal(self.volume) if self.volume else Decimal("0")


class BinanceFuturesMarkPriceResponse(BaseModel):
    """Mark price and funding rate response."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    symbol: str = Field(..., description="Symbol name")
    markPrice: str = Field(..., description="Mark price")
    indexPrice: str = Field(..., description="Index price")
    estimatedSettlePrice: str = Field(..., description="Estimated settle price")
    lastFundingRate: str = Field(..., description="Last funding rate")
    nextFundingTime: int = Field(..., description="Next funding time")
    interestRate: str = Field(..., description="Interest rate")
    time: int = Field(..., description="Response timestamp")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesMarkPriceResponse":
        """Create from API response dict."""
        return cls(
            symbol=data.get("symbol", ""),
            markPrice=data.get("markPrice", "0"),
            indexPrice=data.get("indexPrice", "0"),
            estimatedSettlePrice=data.get("estimatedSettlePrice", "0"),
            lastFundingRate=data.get("lastFundingRate", "0"),
            nextFundingTime=data.get("nextFundingTime", 0),
            interestRate=data.get("interestRate", "0"),
            time=data.get("time", 0),
        )

    def get_mark_price_decimal(self) -> Decimal:
        """Get mark price as Decimal."""
        return Decimal(self.markPrice) if self.markPrice else Decimal("0")

    def get_funding_rate_decimal(self) -> Decimal:
        """Get funding rate as Decimal."""
        return Decimal(self.lastFundingRate) if self.lastFundingRate else Decimal("0")


# WebSocket Models
class BinanceFuturesWebSocketOrderUpdate(BaseModel):
    """
    WebSocket execution report (ORDER_TRADE_UPDATE).

    Event type 'ORDER_TRADE_UPDATE' from user data stream.
    Maintains exact field names from V1 implementation.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    e: str = Field(..., description='Event type: "ORDER_TRADE_UPDATE"')
    E: int = Field(..., description="Event timestamp")
    T: int = Field(..., description="Transaction timestamp")
    o: Dict[str, Any] = Field(..., description="Order data")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesWebSocketOrderUpdate":
        """Create from WebSocket message dict."""
        return cls(
            e=data.get("e", ""),
            E=data.get("E", 0),
            T=data.get("T", 0),
            o=data.get("o", {}),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def order_data(self) -> "BinanceFuturesWebSocketOrder":
        """Get typed order data."""
        return BinanceFuturesWebSocketOrder.from_dict(self.o)


class BinanceFuturesWebSocketOrder(BaseModel):
    """Order data within WebSocket ORDER_TRADE_UPDATE event."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    s: str = Field(..., description="Symbol")
    c: str = Field(..., description="Client order ID")
    S: str = Field(..., description="Side (BUY/SELL)")
    o: str = Field(..., description="Order type")
    f: str = Field(..., description="Time in force")
    q: str = Field(..., description="Order quantity")
    p: str = Field(..., description="Order price")
    ap: str = Field(..., description="Average price")
    sp: str = Field(..., description="Stop price")
    x: str = Field(..., description="Execution type")
    X: str = Field(..., description="Current order status")
    i: int = Field(..., description="Order ID")
    l: str = Field(..., description="Order last filled quantity")
    z: str = Field(..., description="Order filled accumulated quantity")
    L: str = Field(..., description="Last filled price")
    N: Optional[str] = Field(None, description="Commission asset")
    n: Optional[str] = Field(None, description="Commission")
    T: int = Field(..., description="Order trade time")
    t: int = Field(..., description="Trade ID")
    b: str = Field(..., description="Bids notional")
    a: str = Field(..., description="Ask notional")
    m: bool = Field(..., description="Is this trade the maker side?")
    R: bool = Field(..., description="Is this reduce only")
    wt: str = Field(..., description="Stop price working type")
    ot: str = Field(..., description="Original order type")
    ps: str = Field(..., description="Position side")
    cp: bool = Field(..., description="Close position")
    AP: Optional[str] = Field(None, description="Activation price (for trailing stop)")
    cr: Optional[str] = Field(None, description="Callback rate (for trailing stop)")
    rp: str = Field(..., description="Realized profit")
    pP: bool = Field(..., description="Price protection")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesWebSocketOrder":
        """Create from order data dict."""
        return cls(
            s=data.get("s", ""),
            c=data.get("c", ""),
            S=data.get("S", ""),
            o=data.get("o", ""),
            f=data.get("", ""),
            q=data.get("q", "0"),
            p=data.get("p", "0"),
            ap=data.get("ap", "0"),
            sp=data.get("sp", "0"),
            x=data.get("x", ""),
            X=data.get("X", ""),
            i=data.get("i", 0),
            l=data.get("l", "0"),
            z=data.get("z", "0"),
            L=data.get("L", "0"),
            N=data.get("N"),
            n=data.get("n"),
            T=data.get("T", 0),
            t=data.get("t", 0),
            b=data.get("b", "0"),
            a=data.get("a", "0"),
            m=data.get("m", False),
            R=data.get("R", False),
            wt=data.get("wt", ""),
            ot=data.get("ot", ""),
            ps=data.get("ps", ""),
            cp=data.get("cp", False),
            AP=data.get("AP"),
            cr=data.get("cr"),
            rp=data.get("rp", "0"),
            pP=data.get("pP", False),
        )


class BinanceFuturesWebSocketPositionUpdate(BaseModel):
    """
    WebSocket account update (ACCOUNT_UPDATE).

    Event type 'ACCOUNT_UPDATE' from user data stream.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    e: str = Field(..., description='Event type: "ACCOUNT_UPDATE"')
    E: int = Field(..., description="Event timestamp")
    T: int = Field(..., description="Transaction timestamp")
    a: Dict[str, Any] = Field(..., description="Account update data")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesWebSocketPositionUpdate":
        """Create from WebSocket message dict."""
        return cls(
            e=data.get("e", ""),
            E=data.get("E", 0),
            T=data.get("T", 0),
            a=data.get("a", {}),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def balances(self) -> List[Dict[str, Any]]:
        """Get balance updates."""
        result: List[Dict[str, Any]] = self.a.get("B", [])
        return result

    @computed_field  # type: ignore[prop-decorator]
    @property
    def positions(self) -> List[Dict[str, Any]]:
        """Get position updates."""
        result: List[Dict[str, Any]] = self.a.get("P", [])
        return result


class BinanceFuturesWebSocketDepthUpdate(BaseModel):
    """
    WebSocket orderbook depth update.

    From market data stream depth updates.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    e: str = Field(..., description='Event type: "depthUpdate"')
    E: int = Field(..., description="Event timestamp")
    T: int = Field(..., description="Transaction timestamp")
    s: str = Field(..., description="Symbol")
    U: int = Field(..., description="First update ID")
    u: int = Field(..., description="Final update ID")
    pu: int = Field(..., description="Final update ID in last stream")
    b: List[List[str]] = Field(..., description="Bids to update [[price, quantity], ...]")
    a: List[List[str]] = Field(..., description="Asks to update [[price, quantity], ...]")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesWebSocketDepthUpdate":
        """Create from WebSocket message dict."""
        return cls(
            e=data.get("e", ""),
            E=data.get("E", 0),
            T=data.get("T", 0),
            s=data.get("s", ""),
            U=data.get("U", 0),
            u=data.get("u", 0),
            pu=data.get("pu", 0),
            b=data.get("b", []),
            a=data.get("a", []),
        )


class BinanceFuturesWebSocketBookTicker(BaseModel):
    """WebSocket individual book ticker."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    e: str = Field(..., description='Event type: "bookTicker"')
    u: int = Field(..., description="Order book updateId")
    E: int = Field(..., description="Event time")
    T: int = Field(..., description="Transaction time")
    s: str = Field(..., description="Symbol")
    b: str = Field(..., description="Best bid price")
    B: str = Field(..., description="Best bid qty")
    a: str = Field(..., description="Best ask price")
    A: str = Field(..., description="Best ask qty")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesWebSocketBookTicker":
        """Create from WebSocket message dict with strict validation.

        CRITICAL: Uses direct dict access (not .get()) so Pydantic catches missing fields.
        If Binance sends invalid data, this will raise KeyError/ValidationError with clear message.
        """
        return cls(
            e=data["e"],  # Raises KeyError if missing - we want this!
            u=data["u"],
            E=data["E"],
            T=data["T"],
            s=data["s"],
            b=data["b"],  # Must be present or fail
            B=data["B"],
            a=data["a"],  # Must be present or fail
            A=data["A"],
        )

    def get_best_bid_price(self) -> Decimal:
        """Get best bid price as Decimal."""
        return Decimal(self.b) if self.b else Decimal("0")

    def get_best_ask_price(self) -> Decimal:
        """Get best ask price as Decimal."""
        return Decimal(self.a) if self.a else Decimal("0")


class BinanceFuturesWebSocketMarkPrice(BaseModel):
    """WebSocket mark price update."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    e: str = Field(..., description='Event type: "markPriceUpdate"')
    E: int = Field(..., description="Event time")
    s: str = Field(..., description="Symbol")
    p: str = Field(..., description="Mark price")
    i: str = Field(..., description="Index price")
    P: str = Field(..., description="Estimated settle price")
    r: str = Field(..., description="Funding rate")
    T: int = Field(..., description="Next funding time")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesWebSocketMarkPrice":
        """Create from WebSocket message dict."""
        return cls(
            e=data.get("e", ""),
            E=data.get("E", 0),
            s=data.get("s", ""),
            p=data.get("p", "0"),
            i=data.get("i", "0"),
            P=data.get("P", "0"),
            r=data.get("r", "0"),
            T=data.get("T", 0),
        )

    def get_mark_price_decimal(self) -> Decimal:
        """Get mark price as Decimal."""
        return Decimal(self.p) if self.p else Decimal("0")

    def get_funding_rate_decimal(self) -> Decimal:
        """Get funding rate as Decimal."""
        return Decimal(self.r) if self.r else Decimal("0")


class BinanceFuturesListenKeyResponse(BaseModel):
    """Response from listen key creation/renewal."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    listenKey: str = Field(..., description="The listen key for user data stream")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesListenKeyResponse":
        """Create from API response dict."""
        return cls(listenKey=data.get("listenKey", ""))


class BinanceFuturesErrorResponse(BaseModel):
    """Binance Futures API error response."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    code: int = Field(..., description="Error code")
    msg: str = Field(..., description="Error message")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinanceFuturesErrorResponse":
        """Create from API response dict."""
        return cls(
            code=data.get("code", 0),
            msg=data.get("msg", ""),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_rate_limit_error(self) -> bool:
        """Check if this is a rate limit error."""
        return self.code == -1003

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_insufficient_balance_error(self) -> bool:
        """Check if this is an insufficient balance error."""
        return self.code in [-2018, -2019]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_order_not_found_error(self) -> bool:
        """Check if this is an order not found error."""
        return self.code == -2013

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_authentication_error(self) -> bool:
        """Check if this is an authentication error."""
        return self.code in [-1002, -1022, -2014, -2015]

    def __str__(self) -> str:
        """String representation of the error."""
        return f"BinanceFuturesError(code={self.code}, message={self.msg!r})"


# Type alias for WebSocket messages
BinanceFuturesWebSocketMessage = Union[
    BinanceFuturesWebSocketOrderUpdate,
    BinanceFuturesWebSocketPositionUpdate,
    BinanceFuturesWebSocketDepthUpdate,
    BinanceFuturesWebSocketBookTicker,
    BinanceFuturesWebSocketMarkPrice,
    Dict[str, Any],  # Fallback for unknown message types
]


# =============================================================================
# RESPONSE ENVELOPE TYPES
# =============================================================================
# These types centralize isinstance checks for API response unwrapping.
# Instead of checking isinstance in multiple places, parse once at adapter entry.


class BinanceFuturesPositionListEnvelope(BaseModel):
    """Envelope for Binance Futures position list responses.

    Binance position responses can be:
    - Direct list: [position1, position2, ...]
    - Wrapped dict: {"positions": [position1, position2, ...]}

    This model normalizes both to a consistent interface.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    positions: List[Dict[str, Any]] = Field(default_factory=list, description="List of positions")

    @classmethod
    def from_response(cls, response: Union[Dict[str, Any], List[Any]]) -> "BinanceFuturesPositionListEnvelope":
        """Create envelope from raw API response.

        Handles both list and dict formats.
        """
        if isinstance(response, list):
            return cls(positions=response)
        if isinstance(response, dict) and "positions" in response:
            return cls(positions=response["positions"])
        # Single position dict
        return cls(positions=[response])

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items(self) -> List[Dict[str, Any]]:
        """Get position list (alias for consistency with other envelopes)."""
        return self.positions


class BinanceFuturesBalanceEnvelope(BaseModel):
    """Envelope for Binance Futures balance/account responses.

    Handles account info with assets and positions arrays.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    assets: List[Dict[str, Any]] = Field(default_factory=list, description="List of asset balances")

    @classmethod
    def from_response(cls, response: Union[Dict[str, Any], List[Any]]) -> "BinanceFuturesBalanceEnvelope":
        """Create envelope from raw API response."""
        if isinstance(response, list):
            return cls(assets=response)
        if isinstance(response, dict) and "assets" in response:
            return cls(assets=response["assets"])
        # Single balance or direct list
        return cls(assets=[response] if isinstance(response, dict) else [])

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items(self) -> List[Dict[str, Any]]:
        """Get asset list (alias for consistency)."""
        return self.assets
