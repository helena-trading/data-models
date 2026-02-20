"""Lightweight logging utilities for data-models.

This module keeps the API shape used by core while avoiding cross-repo imports.
"""

import logging
import os
import threading
import time
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

_thread_local = threading.local()
_run_ctx: ContextVar[Optional[int]] = ContextVar("run_id", default=None)
_bot_ctx: ContextVar[Optional[int]] = ContextVar("bot_id", default=None)
_route_ctx: ContextVar[Optional[str]] = ContextVar("route", default=None)
_lifecycle_ctx: ContextVar[Optional[str]] = ContextVar("lifecycle_id", default=None)
_order_ctx: ContextVar[Optional[str]] = ContextVar("order_id", default=None)
_component_ctx: ContextVar[Optional[str]] = ContextVar("component", default=None)

_logger: Optional[logging.Logger] = None


def set_current_route(route: Optional[str]) -> None:
    _thread_local.route = route
    _route_ctx.set(route)


def get_current_route() -> Optional[str]:
    return getattr(_thread_local, "route", None) or _route_ctx.get()


def set_current_lifecycle_id(lifecycle_id: Optional[str]) -> None:
    _thread_local.lifecycle_id = lifecycle_id
    _lifecycle_ctx.set(lifecycle_id)


def get_current_lifecycle_id() -> Optional[str]:
    return getattr(_thread_local, "lifecycle_id", None) or _lifecycle_ctx.get()


def set_current_run_id(run_id: Optional[int]) -> None:
    _thread_local.run_id = run_id
    _run_ctx.set(run_id)


def get_current_run_id() -> Optional[int]:
    return getattr(_thread_local, "run_id", None) or _run_ctx.get()


def set_current_bot_id(bot_id: Optional[int]) -> None:
    _thread_local.bot_id = bot_id
    _bot_ctx.set(bot_id)


def get_current_bot_id() -> Optional[int]:
    return getattr(_thread_local, "bot_id", None) or _bot_ctx.get()


def set_current_order_id(order_id: Optional[str]) -> None:
    _thread_local.order_id = order_id
    _order_ctx.set(order_id)


def get_current_order_id() -> Optional[str]:
    return getattr(_thread_local, "order_id", None) or _order_ctx.get()


def set_component(component: Optional[str]) -> None:
    _thread_local.component = component
    _component_ctx.set(component)


def get_component() -> Optional[str]:
    return getattr(_thread_local, "component", None) or _component_ctx.get()


def set_context(
    *,
    run_id: Optional[int] = None,
    bot_id: Optional[int] = None,
    lifecycle_id: Optional[str] = None,
    route: Optional[str] = None,
    order_id: Optional[str] = None,
    component: Optional[str] = None,
) -> None:
    if run_id is not None:
        set_current_run_id(run_id)
    if bot_id is not None:
        set_current_bot_id(bot_id)
    if lifecycle_id is not None:
        set_current_lifecycle_id(lifecycle_id)
    if route is not None:
        set_current_route(route)
    if order_id is not None:
        set_current_order_id(order_id)
    if component is not None:
        set_component(component)


def initialize_logging_context(component: str) -> int:
    set_component(component)
    raw_run_id = os.environ.get("RUN_ID")
    if raw_run_id:
        try:
            run_id = int(raw_run_id)
            set_context(run_id=run_id)
            return run_id
        except ValueError:
            pass

    run_id = int(time.time())
    set_context(run_id=run_id)
    return run_id


def _prefix_message(message: str) -> str:
    parts = []
    run_id = get_current_run_id()
    if run_id is not None:
        parts.append(f"[RUN:{run_id}]")
    route = get_current_route()
    if route:
        parts.append(f"[{route}]")
    lifecycle_id = get_current_lifecycle_id()
    if lifecycle_id:
        parts.append(f"[LIFE:{lifecycle_id}]")
    component = get_component()
    if component:
        parts.append(f"[{component}]")
    return f"{''.join(parts)} {message}" if parts else message


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    global _logger

    level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("data_models")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)

    _logger = logger
    return logger


def _ensure_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
    return _logger


def get_logger() -> logging.Logger:
    return _ensure_logger()


def get_adapter() -> logging.LoggerAdapter:
    return logging.LoggerAdapter(_ensure_logger(), {})


def set_log_level(level: str) -> None:
    logger = _ensure_logger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_log_dir() -> str:
    return os.environ.get("LOG_DIR", "./logs")


def get_timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


def debug(message: str) -> None:
    _ensure_logger().debug(_prefix_message(message))


def info(message: str) -> None:
    _ensure_logger().info(_prefix_message(message))


def warning(message: str) -> None:
    _ensure_logger().warning(_prefix_message(message))


def error(message: str) -> None:
    _ensure_logger().error(_prefix_message(message))


def critical(message: str) -> None:
    _ensure_logger().critical(_prefix_message(message))
