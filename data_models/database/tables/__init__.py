"""Database table models with lazy exports.

This package intentionally avoids eager importing of every table module.
Some table modules depend on optional runtime-only components, so we resolve
symbols lazily when accessed.
"""

from __future__ import annotations

import importlib
from typing import Dict

# Symbol -> module path
_SYMBOL_TO_MODULE: Dict[str, str] = {
    "Account": "data_models.database.tables.account",
    "AccountBalance": "data_models.database.tables.account_balance",
    "AccountType": "data_models.database.tables.account",
    "AdminUser": "data_models.database.tables.admin_user",
    "BlockTrade": "data_models.database.tables.block_trade",
    "Bot": "data_models.database.tables.bot",
    "BotAccount": "data_models.database.tables.account",
    "BotAccountRole": "data_models.database.tables.account",
    "BotActivityLog": "data_models.database.tables.bot",
    "BotHealthStatus": "data_models.database.tables.bot_health_status",
    "BotParameter": "data_models.database.tables.bot_parameter",
    "BotParameterHistory": "data_models.database.tables.bot_parameter",
    "BotRun": "data_models.database.tables.bot",
    "BotRunUpdate": "data_models.database.tables.bot_run_update",
    "BotStatus": "data_models.database.tables.bot",
    "ChatConversation": "data_models.database.tables.chat_conversation",
    "ChatMessage": "data_models.database.tables.chat_message",
    "ChatUserPreferences": "data_models.database.tables.chat_user_preferences",
    "CoreProcessConfig": "data_models.database.tables.core_process",
    "CredentialAuditLog": "data_models.database.tables.encrypted_credential",
    "EncryptedCredential": "data_models.database.tables.encrypted_credential",
    "ErrorLog": "data_models.database.tables.error_log",
    "FundingEngineAdjustment": "data_models.database.tables.funding_engine_adjustment",
    "FundingEngineSpreadImpact": "data_models.database.tables.funding_engine_spread_impact",
    "FundingPrediction": "data_models.database.tables.funding_prediction",
    "FundingRateSnapshot": "data_models.database.tables.funding_rate_snapshot",
    "LatencyMetric": "data_models.database.tables.latency_metric",
    "LogLevel": "data_models.database.tables.bot",
    "MarketData": "data_models.database.tables.market_data",
    "MarketDataHubConfig": "data_models.database.tables.market_data_hub",
    "OpenInterestSnapshot": "data_models.database.tables.market_metrics_snapshot",
    "OrderExecution": "data_models.database.tables.order_execution",
    "OrdersCommandHubConfig": "data_models.database.tables.orders_command_hub",
    "OrdersCommandHubTrackedAccount": "data_models.database.tables.orders_command_hub",
    "PositionHistory": "data_models.database.tables.position_history",
    "PositionSnapshot": "data_models.database.tables.position_snapshot",
    "PricingSpreadSnapshot": "data_models.database.tables.pricing_spread_snapshot",
    "PrivateDataHubConfig": "data_models.database.tables.private_data_hub",
    "PrivateDataHubTrackedAccount": "data_models.database.tables.private_data_hub",
    "ReferencePrice": "data_models.database.tables.reference_price",
    "SpreadNormalizationEvent": "data_models.database.tables.spread_normalization_event",
    "UserSettings": "data_models.database.tables.user_settings",
    "VolumeSnapshot": "data_models.database.tables.market_metrics_snapshot",
}

__all__ = sorted(_SYMBOL_TO_MODULE.keys())


def __getattr__(name: str):
    module_name = _SYMBOL_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value

