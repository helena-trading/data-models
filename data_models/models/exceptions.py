"""
Standardized error hierarchy for model-related operations.

This module defines a consistent set of exception classes for handling
errors that can occur when working with model objects like Orders,
TradingPairs, Balances, etc.
"""

from typing import Any, Dict, Optional


class ModelError(Exception):
    """Base class for all model-related errors.

    This is the parent class for all model-related exceptions and
    can be used to catch any model-related error.
    """

    def __init__(self, message: Optional[str] = None, model_type: Optional[str] = None, **kwargs: Any) -> None:  # noqa: B042
        """Initialize with model type and additional context.

        Args:
            message: Error message
            model_type: Type of model that caused the error (e.g., "Order", "TradingPair")
            **kwargs: Additional error metadata
        """
        self.message = message or "Model error"
        self.model_type = model_type
        self.data = kwargs

        # Build detail string
        details = f" [{model_type}]" if model_type else ""
        if kwargs:
            for key, value in kwargs.items():
                details += f", {key}={value}"

        super().__init__(f"{self.message}{details}")


class DataValidationError(ModelError):
    """Error for invalid model data or validation failures.

    This includes missing required fields, invalid data types,
    out-of-range values, etc.
    """

    def __init__(  # noqa: B042
        self,
        message: Optional[str] = None,
        model_type: Optional[str] = None,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with field-specific validation context.

        Args:
            message: Error message
            model_type: Type of model being validated
            field: Name of the field that failed validation
            value: The invalid value
            **kwargs: Additional error metadata
        """
        self.field = field
        self.value = value

        if field:
            kwargs["field"] = field
        if value is not None:
            kwargs["value"] = str(value)

        if not message:
            if field:
                message = f"Invalid value for field {field!r}"
            else:
                message = "Data validation failed"

        super().__init__(message, model_type, **kwargs)


class DataParsingError(ModelError):
    """Error for parsing exchange-specific data into models.

    This includes malformed responses, missing required fields from exchanges,
    unexpected data formats, etc.
    """

    def __init__(  # noqa: B042
        self,
        message: Optional[str] = None,
        model_type: Optional[str] = None,
        exchange: Optional[str] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with parsing context.

        Args:
            message: Error message
            model_type: Type of model being parsed
            exchange: Exchange identifier where the error occurred
            raw_data: Raw exchange data that failed to parse
            **kwargs: Additional error metadata
        """
        self.exchange = exchange
        self.raw_data = raw_data

        if exchange:
            kwargs["exchange"] = exchange
        if raw_data:
            kwargs["raw_data_keys"] = list(raw_data.keys()) if isinstance(raw_data, dict) else str(type(raw_data))

        if not message:
            if exchange:
                message = f"Failed to parse {exchange} data"
            else:
                message = "Data parsing failed"

        super().__init__(message, model_type, **kwargs)


class ConfigurationError(ModelError):
    """Error for invalid model configuration.

    This includes missing required configuration parameters,
    invalid parameter combinations, etc.
    """

    def __init__(  # noqa: B042
        self,
        message: Optional[str] = None,
        model_type: Optional[str] = None,
        parameter: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with configuration context.

        Args:
            message: Error message
            model_type: Type of model with configuration error
            parameter: Name of the invalid parameter
            **kwargs: Additional error metadata
        """
        self.parameter = parameter

        if parameter:
            kwargs["parameter"] = parameter

        if not message:
            if parameter:
                message = f"Invalid configuration parameter: {parameter}"
            else:
                message = "Configuration error"

        super().__init__(message, model_type, **kwargs)


class ModelNotFoundError(ModelError):
    """Error when a requested model object cannot be found.

    This occurs when looking up orders, trading pairs, or other model
    objects that don't exist in cache or storage.
    """

    def __init__(  # noqa: B042
        self,
        message: Optional[str] = None,
        model_type: Optional[str] = None,
        identifier: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with lookup context.

        Args:
            message: Error message
            model_type: Type of model that wasn't found
            identifier: The identifier used for lookup
            **kwargs: Additional error metadata
        """
        self.identifier = identifier

        if identifier:
            kwargs["identifier"] = identifier

        if not message:
            if identifier:
                message = f"Model not found: {identifier}"
            else:
                message = "Model not found"

        super().__init__(message, model_type, **kwargs)


class ModelCacheError(ModelError):
    """Error for cache-related operations.

    This includes cache corruption, size limit violations,
    inconsistent state, etc.
    """

    def __init__(  # noqa: B042
        self,
        message: Optional[str] = None,
        model_type: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with cache operation context.

        Args:
            message: Error message
            model_type: Type of model in cache
            operation: Cache operation that failed (e.g., "add", "update", "lookup")
            **kwargs: Additional error metadata
        """
        self.operation = operation

        if operation:
            kwargs["operation"] = operation

        if not message:
            if operation:
                message = f"Cache operation failed: {operation}"
            else:
                message = "Cache error"

        super().__init__(message, model_type, **kwargs)


class NumericConversionError(DataValidationError, ValueError):
    """Error for numeric value conversion failures.

    This includes cases where strings cannot be converted to float/int,
    numeric values are out of valid range, etc.

    Inherits from both DataValidationError and ValueError for compatibility.
    """

    def __init__(  # noqa: B042
        self,
        message: Optional[str] = None,
        model_type: Optional[str] = None,
        field: Optional[str] = None,
        value: Any = None,
        target_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with numeric conversion context.

        Args:
            message: Error message
            model_type: Type of model being processed
            field: Name of the field being converted
            value: The value that failed conversion
            target_type: The target numeric type (e.g., "float", "int")
            **kwargs: Additional error metadata
        """
        self.target_type = target_type

        if target_type:
            kwargs["target_type"] = target_type

        if not message:
            if field and target_type:
                message = f"Cannot convert field {field!r} to {target_type}"
            elif field:
                message = f"Numeric conversion failed for field {field!r}"
            else:
                message = "Numeric conversion failed"

        super().__init__(message, model_type, field, value, **kwargs)
