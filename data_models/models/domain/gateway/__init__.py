"""
Gateway domain models package.

Contains health monitoring and status models for exchange gateways.
"""

from .health import GatewayHealthSnapshot

__all__ = ["GatewayHealthSnapshot"]
