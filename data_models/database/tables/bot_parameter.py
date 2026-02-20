"""
Bot Parameter Model for dynamic parameter management.

This module provides database models for storing and managing bot parameters
that can be updated dynamically (hot-reload).

Parameter definitions are sourced from the hierarchical parameter registry.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import validates

from data_models.models.parameters.registry import (
    PARAMETER_GROUPS,
    ParameterType,
    get_parameter_definition,
    validate_parameter_value,
)
from data_models.database.tables.base import Base


class BotParameter(Base):  # type: ignore[misc,no-any-unimported]
    """Model for storing bot trading parameters that can be updated dynamically"""

    __tablename__ = "bot_parameters"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    parameter_name = Column(String(50), nullable=False)
    parameter_value = Column(JSON, nullable=False)
    parameter_type = Column(String(20), nullable=False)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100))
    change_reason = Column(Text)
    previous_value = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "parameter_type IN ('float', 'int', 'bool', 'string')",
            name="check_parameter_type",
        ),
        Index("idx_bot_parameters_bot_id_name", "bot_id", "parameter_name", unique=True),
        Index("idx_bot_parameters_bot_id", "bot_id"),
        Index("idx_bot_parameters_name", "parameter_name"),
        Index("idx_bot_parameters_updated_at", "updated_at"),
    )

    @validates("parameter_value")
    def validate_parameter_value(self, key: str, value: Any) -> Any:
        """Validate parameter value based on type and range"""
        if self.parameter_type == "float":
            try:
                float_val = float(value)
                if self.min_value is not None and float_val < self.min_value:
                    raise ValueError(f"Value {float_val} is below minimum {self.min_value}")
                if self.max_value is not None and float_val > self.max_value:
                    raise ValueError(f"Value {float_val} is above maximum {self.max_value}")
                return float_val
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid float value: {value}") from e

        elif self.parameter_type == "int":
            try:
                int_val = int(value)
                if self.min_value is not None and int_val < self.min_value:
                    raise ValueError(f"Value {int_val} is below minimum {self.min_value}")
                if self.max_value is not None and int_val > self.max_value:
                    raise ValueError(f"Value {int_val} is above maximum {self.max_value}")
                return int_val
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid integer value: {value}") from e

        elif self.parameter_type == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)

        else:  # string
            return str(value)

    def get_typed_value(self) -> Union[float, int, bool, str]:
        """Get the parameter value with correct type"""
        if self.parameter_type == "float":
            return float(self.parameter_value)
        elif self.parameter_type == "int":
            return int(self.parameter_value)
        elif self.parameter_type == "bool":
            # Value is already validated and stored as bool by validate_parameter_value
            # JSON preserves bool type, so direct return is safe
            return bool(self.parameter_value)
        else:
            return str(self.parameter_value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary"""
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "parameter_name": self.parameter_name,
            "parameter_value": self.get_typed_value(),
            "parameter_type": self.parameter_type,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
            "change_reason": self.change_reason,
        }

    def __repr__(self) -> str:
        return f"<BotParameter(name={self.parameter_name}, value={self.parameter_value}, type={self.parameter_type})>"


class BotParameterHistory(Base):  # type: ignore[misc,no-any-unimported]
    """Model for tracking parameter change history"""

    __tablename__ = "bot_parameters_history"

    id = Column(Integer, primary_key=True)
    parameter_name = Column(String(50), nullable=False)
    old_value = Column(JSON)
    new_value = Column(JSON, nullable=False)
    changed_by = Column(String(100))
    change_reason = Column(Text)
    changed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_bot_parameters_history_name", "parameter_name"),
        Index("idx_bot_parameters_history_changed_at", "changed_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert history entry to dictionary"""
        return {
            "id": self.id,
            "parameter_name": self.parameter_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by": self.changed_by,
            "change_reason": self.change_reason,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }

    def __repr__(self) -> str:
        return f"<BotParameterHistory(name={self.parameter_name}, old={self.old_value}, new={self.new_value})>"


def _generate_flat_parameter_definitions() -> Dict[str, Dict[str, Any]]:
    """Generate flat PARAMETER_DEFINITIONS from the hierarchical registry.

    This provides backward compatibility for code that still uses flat parameter names.
    Maps hierarchical group.param to flat parameter names.
    """
    definitions: Dict[str, Dict[str, Any]] = {}

    # Mapping from hierarchical to flat names (for backward compatibility)
    flat_name_map = {
        # Sizing group
        ("sizing", "amount_cap"): "trade_amt_cap",
        ("sizing", "amount_floor"): "trade_amt_floor",
        ("sizing", "max_notional_premium"): "maximum_amount_premium",
        ("sizing", "max_notional_discount"): "maximum_amount_discount",
        # Taker reference group
        ("taker_reference", "depth_capture_pct"): "taker_ref_depth_capture_pct",
        ("taker_reference", "levels"): "taker_ref_levels",
        ("taker_reference", "size_floor"): "taker_ref_size_floor",
        ("taker_reference", "size_cap"): "taker_ref_size_cap",
        # Funding group
        ("funding", "horizon_hours"): "funding_adjustment_horizon",
        ("funding", "safety_buffer"): "funding_safety_buffer",
        ("funding", "refresh_interval_sec"): "funding_refresh_interval",
        # Execution group
        ("execution", "wait_for_fill"): "wait_for_taker_fill",
        ("execution", "taker_timeout_ms"): "taker_latency_timeout",
        ("execution", "maker_staleness_threshold_ms"): "maker_staleness_threshold_ms",
        ("execution", "taker_staleness_threshold_ms"): "taker_staleness_threshold_ms",
        # Slippage sizing - premium
        ("slippage_sizing.premium", "budget_bps"): "slippage_budget_bps_premium",
        ("slippage_sizing.premium", "capture_pct"): "slippage_capture_pct_premium",
        # Slippage sizing - discount
        ("slippage_sizing.discount", "budget_bps"): "slippage_budget_bps_discount",
        ("slippage_sizing.discount", "capture_pct"): "slippage_capture_pct_discount",
        # Slippage penalty parameters
        ("slippage_penalty", "enabled"): "slippage_penalty_enabled",
        ("slippage_penalty", "scale_factor"): "slippage_penalty_scale_factor",
        ("slippage_penalty", "max_penalty_bps"): "slippage_penalty_max_penalty_bps",
    }

    for group_name, group in PARAMETER_GROUPS.items():
        # Add parameters from this group
        for param in group.parameters:
            # Get flat name from map, or use group_param format
            flat_key = flat_name_map.get((group_name, param.name), param.name)

            definitions[flat_key] = {
                "type": param.type.value,
                "min": param.min_value,
                "max": param.max_value,
                "default": param.default,
                "description": param.description,
                "group": group_name,
                "param": param.name,
            }

        # Handle subgroups (e.g., slippage_sizing.premium, slippage_sizing.discount)
        if group.subgroups:
            for subgroup_name, subgroup in group.subgroups.items():
                for param in subgroup.parameters:
                    # Get flat name from map, fallback to generated name
                    subgroup_key = f"{group_name}.{subgroup_name}"
                    flat_key = flat_name_map.get((subgroup_key, param.name)) or f"{group_name}_{subgroup_name}_{param.name}"

                    definitions[flat_key] = {
                        "type": param.type.value,
                        "min": param.min_value,
                        "max": param.max_value,
                        "default": param.default,
                        "description": param.description,
                        "group": group_name,
                        "subgroup": subgroup_name,
                        "param": param.name,
                    }

    # Add aliases for backward compatibility
    aliases = {
        "wait_exec": definitions.get("wait_for_taker_fill", {}),
        "max_amount_premium": definitions.get("maximum_amount_premium", {}),
        "max_amount_discount": definitions.get("maximum_amount_discount", {}),
        "taker_ref_enabled": {
            "type": "bool",
            "default": True,
            "description": "Enable taker reference pricing (None in hierarchical = disabled)",
        },
        "slippage_sizing_enabled": {
            "type": "bool",
            "default": True,
            "description": "Enable slippage-bounded sizing (None in hierarchical = disabled)",
        },
        "enable_funding_adjustment": {
            "type": "bool",
            "default": False,
            "description": "Enable funding rate adjustment (None in hierarchical = disabled)",
        },
    }
    for alias_name, alias_def in aliases.items():
        if alias_def and alias_name not in definitions:
            definitions[alias_name] = dict(alias_def)
            definitions[alias_name]["is_alias"] = True

    return definitions


# Parameter definitions generated from hierarchical registry
# This provides backward compatibility for flat parameter access
PARAMETER_DEFINITIONS = _generate_flat_parameter_definitions()
