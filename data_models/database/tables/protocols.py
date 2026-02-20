"""Database Model Protocols

Type-safe interfaces for database model operations.
Used to provide compile-time type checking for batch operations.
"""

from typing import Any, Protocol, Tuple, runtime_checkable


@runtime_checkable
class BatchInsertable(Protocol):
    """Protocol for models that support batch insert operations."""

    @staticmethod
    def batch_insert_query() -> str:
        """Get the SQL query for batch inserts."""
        ...

    def to_insert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Get INSERT query and parameters for this instance."""
        ...


@runtime_checkable
class BatchUpsertable(Protocol):
    """Protocol for models that support batch upsert operations."""

    @staticmethod
    def batch_upsert_query() -> str:
        """Get the SQL query for batch upserts."""
        ...

    def to_upsert_query(self) -> Tuple[str, Tuple[Any, ...]]:
        """Get UPSERT query and parameters for this instance."""
        ...
