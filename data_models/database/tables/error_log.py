"""Error log model for database storage."""

import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Removed unused import


@dataclass
class ErrorLog:
    """Model for error log entries."""

    time: datetime
    level: str  # ERROR, CRITICAL, WARNING
    component: str  # Component/module that generated the error
    message: str
    error_type: Optional[str] = None  # Type/class of error
    exchange: Optional[str] = None  # Exchange where error occurred
    traceback: Optional[str] = None  # Full traceback
    context: Optional[Dict[str, Any]] = field(default_factory=dict)  # Additional context
    route_id: Optional[int] = None
    order_id: Optional[int] = None
    resolved: bool = False
    resolution_notes: Optional[str] = None
    bot_id: Optional[int] = None  # Bot that generated the error
    run_id: Optional[int] = None  # Run ID for filtering logs by run

    @classmethod
    def from_exception(
        cls,
        e: Exception,
        component: str,
        level: str = "ERROR",
        exchange: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        bot_id: Optional[int] = None,
        run_id: Optional[int] = None,
    ) -> "ErrorLog":
        """Create ErrorLog from an exception.

        Args:
            e: The exception
            component: Component/module name
            level: Log level (ERROR, CRITICAL, WARNING)
            exchange: Exchange name if applicable
            context: Additional context data
            bot_id: Bot ID (if not provided, attempts to get from thread context)
            run_id: Run ID (if not provided, attempts to get from thread context)

        Returns:
            ErrorLog instance
        """
        # Get the full traceback
        tb_str = traceback.format_exc()

        # Get error type from exception class
        error_type = type(e).__name__

        # Get current route if available
        route_id = None
        try:
            from data_models.logging.logger import (
                get_current_route,
            )

            route = get_current_route()
            # Ensure route_id fits in PostgreSQL integer range (-2147483648 to 2147483647)
            # Use abs() to ensure positive value, then fit in range
            route_id = abs(hash(route)) % 2147483647 if route else None
        except Exception:
            pass

        # Get run_id and bot_id from thread context if not provided
        if run_id is None or bot_id is None:
            try:
                from data_models.logging.logger import (
                    get_current_bot_id,
                    get_current_run_id,
                )

                if run_id is None:
                    run_id = get_current_run_id()
                if bot_id is None:
                    bot_id = get_current_bot_id()
            except Exception:
                pass

        return cls(
            time=datetime.utcnow(),
            level=level,
            component=component,
            message=str(e),
            error_type=error_type,
            exchange=exchange,
            traceback=tb_str,
            context=context or {},
            route_id=route_id,
            bot_id=bot_id,
            run_id=run_id,
        )

    @classmethod
    def from_message(
        cls,
        message: str,
        component: str,
        level: str = "ERROR",
        exchange: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        bot_id: Optional[int] = None,
        run_id: Optional[int] = None,
    ) -> "ErrorLog":
        """Create ErrorLog from a message string.

        Args:
            message: Error message
            component: Component/module name
            level: Log level (ERROR, CRITICAL, WARNING)
            exchange: Exchange name if applicable
            context: Additional context data
            bot_id: Bot ID (if not provided, attempts to get from thread context)
            run_id: Run ID (if not provided, attempts to get from thread context)

        Returns:
            ErrorLog instance
        """
        # Get current route if available
        route_id = None
        try:
            from data_models.logging.logger import (
                get_current_route,
            )

            route = get_current_route()
            # Ensure route_id fits in PostgreSQL integer range (-2147483648 to 2147483647)
            # Use abs() to ensure positive value, then fit in range
            route_id = abs(hash(route)) % 2147483647 if route else None
        except Exception:
            pass

        # Get run_id and bot_id from thread context if not provided
        if run_id is None or bot_id is None:
            try:
                from data_models.logging.logger import (
                    get_current_bot_id,
                    get_current_run_id,
                )

                if run_id is None:
                    run_id = get_current_run_id()
                if bot_id is None:
                    bot_id = get_current_bot_id()
            except Exception:
                pass

        return cls(
            time=datetime.utcnow(),
            level=level,
            component=component,
            message=message,
            exchange=exchange,
            context=context or {},
            route_id=route_id,
            bot_id=bot_id,
            run_id=run_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "time": self.time,
            "level": self.level,
            "component": self.component,
            "message": self.message,
            "error_type": self.error_type,
            "exchange": self.exchange,
            "traceback": self.traceback,
            "context": json.dumps(self.context) if self.context else None,
            "route_id": self.route_id,
            "order_id": self.order_id,
            "resolved": self.resolved,
            "resolution_notes": self.resolution_notes,
            "bot_id": self.bot_id,
            "run_id": self.run_id,
        }

    def to_insert_query(self) -> Tuple[str, List[Any]]:
        """Generate INSERT query and parameters."""
        query = """
            INSERT INTO error_logs (
                time, level, component, message, error_type,
                exchange, traceback, context, route_id, order_id,
                resolved, resolution_notes, bot_id, run_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = [
            self.time,
            self.level,
            self.component,
            self.message,
            self.error_type,
            self.exchange,
            self.traceback,
            json.dumps(self.context) if self.context else None,
            self.route_id,
            self.order_id,
            self.resolved,
            self.resolution_notes,
            self.bot_id,
            self.run_id,
        ]

        return query, params

    @staticmethod
    def batch_insert_query() -> str:
        """Get batch insert query for multiple error logs."""
        return """
            INSERT INTO error_logs (
                time, level, component, message, error_type,
                exchange, traceback, context, route_id, order_id,
                resolved, resolution_notes, bot_id, run_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
