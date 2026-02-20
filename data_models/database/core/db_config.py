"""Database configuration and connection management."""

import logging
import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional, Tuple, Union, cast

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from data_models.logging import error, info

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    host: str = "localhost"
    port: int = 5432
    database: str = "helena_bot"
    user: str = "helena"
    password: str = ""
    min_connections: int = 1  # Reduced from 2 to minimize startup connection attempts
    max_connections: int = 20

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "DatabaseConfig":
        """Create config from dictionary."""
        return cls(
            host=cast(str, config.get("host", "localhost")),
            port=cast(int, config.get("port", 5432)),
            database=cast(str, config.get("database", "helena_bot")),
            user=cast(str, config.get("user", "helena")),
            password=cast(str, config.get("password", "")),
            min_connections=cast(int, config.get("min_connections", 2)),
            max_connections=cast(int, config.get("max_connections", 20)),
        )

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create config from environment variables."""
        # First check for DATABASE_URL
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            # Parse DATABASE_URL format: postgresql://user:password@host:port/database
            from urllib.parse import unquote, urlparse

            url = urlparse(database_url)
            # CRITICAL: URL-decode the password! urlparse doesn't decode automatically
            # Password may contain URL-encoded special chars like %5E (^), %23 (#), etc.
            decoded_password = unquote(url.password) if url.password else ""
            return cls(
                host=url.hostname or "localhost",
                port=url.port or 5432,
                database=url.path.lstrip("/") if url.path else "helena_bot",
                user=url.username or "helena",
                password=decoded_password,
                min_connections=int(os.environ.get("DB_MIN_CONN", "1")),
                max_connections=int(os.environ.get("DB_MAX_CONN", "20")),
            )

        # Fall back to individual environment variables
        password = os.environ.get("DATABASE_PASSWORD", os.environ.get("DB_PASSWORD", "helena123"))

        return cls(
            host=os.environ.get("DATABASE_HOST", os.environ.get("DB_HOST", "localhost")),
            port=int(os.environ.get("DATABASE_PORT", os.environ.get("DB_PORT", "5432"))),
            database=os.environ.get("DATABASE_NAME", os.environ.get("DB_NAME", "helena_bot")),
            user=os.environ.get("DATABASE_USER", os.environ.get("DB_USER", "helena")),
            password=password,
            min_connections=int(os.environ.get("DB_MIN_CONN", "2")),
            max_connections=int(os.environ.get("DB_MAX_CONN", "20")),
        )

    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string for SQLAlchemy with psycopg3."""
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class AnalyticsDatabaseConfig:
    """Analytics database configuration settings."""

    host: str = "localhost"
    port: int = 5432
    database: str = "helena_analytics"
    user: str = "helena"
    password: str = ""
    min_connections: int = 1
    max_connections: int = 20

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "AnalyticsDatabaseConfig":
        """Create config from dictionary."""
        return cls(
            host=cast(str, config.get("host", "localhost")),
            port=cast(int, config.get("port", 5432)),
            database=cast(str, config.get("database", "helena_analytics")),
            user=cast(str, config.get("user", "helena")),
            password=cast(str, config.get("password", "")),
            min_connections=cast(int, config.get("min_connections", 2)),
            max_connections=cast(int, config.get("max_connections", 20)),
        )

    @classmethod
    def from_env(cls) -> "AnalyticsDatabaseConfig":
        """Create config from environment variables.

        Looks for ANALYTICS_DATABASE_URL first, falls back to individual variables.
        If ANALYTICS_DATABASE_URL is not set, falls back to DATABASE_URL (single database mode).
        """
        # First check for ANALYTICS_DATABASE_URL
        analytics_db_url = os.environ.get("ANALYTICS_DATABASE_URL")

        if analytics_db_url:
            # Parse ANALYTICS_DATABASE_URL format: postgresql://user:password@host:port/database
            from urllib.parse import unquote, urlparse

            url = urlparse(analytics_db_url)
            # CRITICAL: URL-decode the password! urlparse doesn't decode automatically
            decoded_password = unquote(url.password) if url.password else ""
            return cls(
                host=url.hostname or "localhost",
                port=url.port or 5432,
                database=url.path.lstrip("/") if url.path else "helena_analytics",
                user=url.username or "helena",
                password=decoded_password,
                min_connections=int(os.environ.get("ANALYTICS_DB_MIN_CONN", "1")),
                max_connections=int(os.environ.get("ANALYTICS_DB_MAX_CONN", "20")),
            )

        # Fallback to DATABASE_URL (single database mode)
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            from urllib.parse import unquote, urlparse

            url = urlparse(database_url)
            decoded_password = unquote(url.password) if url.password else ""
            return cls(
                host=url.hostname or "localhost",
                port=url.port or 5432,
                database=url.path.lstrip("/") if url.path else "helena_bot",
                user=url.username or "helena",
                password=decoded_password,
                min_connections=int(os.environ.get("DB_MIN_CONN", "1")),
                max_connections=int(os.environ.get("DB_MAX_CONN", "20")),
            )

        # Fall back to individual environment variables
        password = os.environ.get(
            "ANALYTICS_DATABASE_PASSWORD", os.environ.get("DATABASE_PASSWORD", os.environ.get("DB_PASSWORD", "helena123"))
        )

        return cls(
            host=os.environ.get(
                "ANALYTICS_DATABASE_HOST", os.environ.get("DATABASE_HOST", os.environ.get("DB_HOST", "localhost"))
            ),
            port=int(
                os.environ.get("ANALYTICS_DATABASE_PORT", os.environ.get("DATABASE_PORT", os.environ.get("DB_PORT", "5432")))
            ),
            database=os.environ.get("ANALYTICS_DATABASE_NAME", "helena_analytics"),
            user=os.environ.get(
                "ANALYTICS_DATABASE_USER", os.environ.get("DATABASE_USER", os.environ.get("DB_USER", "helena"))
            ),
            password=password,
            min_connections=int(os.environ.get("ANALYTICS_DB_MIN_CONN", "2")),
            max_connections=int(os.environ.get("ANALYTICS_DB_MAX_CONN", "20")),
        )

    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string for SQLAlchemy with psycopg3."""
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class BaseDatabaseManager(ABC):
    """
    Base class for database managers with shared connection pool operations.

    Provides common functionality for connection management, cursor handling,
    and query execution. Subclasses implement the singleton pattern and
    initialization logic.
    """

    def __init__(self) -> None:
        """Initialize base database manager."""
        self.config: Optional[Union[DatabaseConfig, AnalyticsDatabaseConfig]] = None
        self.pool: Optional[ConnectionPool] = None

    @property
    @abstractmethod
    def _log_prefix(self) -> str:
        """Return the log prefix for this database manager (e.g., '[Database]')."""
        pass

    @property
    @abstractmethod
    def _not_initialized_error(self) -> str:
        """Return the error message when database is not initialized."""
        pass

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Get a database connection from the pool."""
        if self.pool is None:
            raise RuntimeError(self._not_initialized_error)

        with self.pool.connection() as conn:
            try:
                yield conn
            except Exception as e:
                conn.rollback()
                raise e from e

    @contextmanager
    def get_cursor(self, commit: bool = True) -> Generator[Any, None, None]:
        """Get a database cursor with automatic transaction management."""
        with self.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                try:
                    yield cur
                    if commit:
                        conn.commit()
                except Exception as e:
                    conn.rollback()
                    raise e from e

    def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None, commit: bool = True) -> Optional[Dict[str, Any]]:
        """Execute a single query and return result."""
        with self.get_cursor(commit=commit) as cur:
            cur.execute(query, params)
            if cur.description:
                return cast(Optional[Dict[str, Any]], cur.fetchone())
            return None

    def execute_many(self, query: str, params_list: List[Any], commit: bool = True) -> None:
        """Execute a query with multiple parameter sets (batch insert)."""
        with self.get_cursor(commit=commit) as cur:
            cur.executemany(query, params_list)

    def fetch_all(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[Any]:
        """Execute a query and fetch all results."""
        with self.get_cursor(commit=False) as cur:
            cur.execute(query, params)
            return cast(List[Any], cur.fetchall())

    def fetch_one(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> Optional[Dict[str, Any]]:
        """Execute a query and fetch one result."""
        with self.get_cursor(commit=False) as cur:
            cur.execute(query, params)
            return cast(Optional[Dict[str, Any]], cur.fetchone())

    def close(self) -> None:
        """Close all database connections."""
        if self.pool:
            self.pool.close()
            self.pool = None
            info(f"{self._log_prefix} Connection pool closed")

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()


class DatabaseManager(BaseDatabaseManager):
    """Manages database connections with connection pooling."""

    _instance: Optional["DatabaseManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "DatabaseManager":
        """Singleton pattern for database manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize database manager (only once)."""
        if not self._initialized:
            super().__init__()
            self._initialized = True

    @property
    def _log_prefix(self) -> str:
        """Return the log prefix for this database manager."""
        return "[Database]"

    @property
    def _not_initialized_error(self) -> str:
        """Return the error message when database is not initialized."""
        return "Database not initialized. Call initialize() first."

    def initialize(self, config: DatabaseConfig) -> None:
        """Initialize the database connection pool."""
        if self.pool is not None:
            info("[Database] Already initialized, skipping")
            return

        self.config = config

        try:
            # Create connection pool with psycopg3
            # Add connect_timeout to the connection string to prevent hanging during connection
            # CRITICAL: Use a longer connect_timeout as RDS connections can be slow
            conninfo = (
                f"host={config.host} port={config.port} dbname={config.database} "
                f"user={config.user} password={config.password} connect_timeout=30"
            )
            self.pool = ConnectionPool(
                conninfo=conninfo,
                min_size=config.min_connections,
                max_size=config.max_connections,
                timeout=30,  # Connection acquisition timeout in seconds
            )

            # Pool is opened automatically on creation (default open=True)
            # Test connection
            with self.pool.connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    if result and result.get("?column?") == 1:
                        info(f"[Database] Successfully connected to {config.host}:{config.port}/{config.database}")
                    else:
                        raise Exception("Database connection test failed")

        except Exception as e:
            error(f"[Database] Failed to initialize: {str(e)}")
            raise

    # Connection pool methods (get_connection, get_cursor, execute, execute_many,
    # fetch_all, fetch_one, close, __del__) inherited from BaseDatabaseManager


class AnalyticsDatabaseManager(BaseDatabaseManager):
    """Manages analytics database connections with connection pooling."""

    _instance: Optional["AnalyticsDatabaseManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "AnalyticsDatabaseManager":
        """Singleton pattern for analytics database manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize analytics database manager (only once)."""
        if not self._initialized:
            super().__init__()
            self._initialized = True

    @property
    def _log_prefix(self) -> str:
        """Return the log prefix for this database manager."""
        return "[Analytics Database]"

    @property
    def _not_initialized_error(self) -> str:
        """Return the error message when database is not initialized."""
        return "Analytics database not initialized. Call initialize() first."

    def initialize(self, config: AnalyticsDatabaseConfig) -> None:
        """Initialize the analytics database connection pool."""
        if self.pool is not None:
            info("[Analytics Database] Already initialized, skipping")
            return

        self.config = config

        try:
            # Create connection pool with psycopg3
            conninfo = (
                f"host={config.host} port={config.port} dbname={config.database} "
                f"user={config.user} password={config.password} connect_timeout=30"
            )
            self.pool = ConnectionPool(
                conninfo=conninfo,
                min_size=config.min_connections,
                max_size=config.max_connections,
                timeout=30,  # Connection acquisition timeout in seconds
            )

            # Pool is opened automatically on creation (default open=True)
            # Test connection
            with self.pool.connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    if result and result.get("?column?") == 1:
                        info(f"[Analytics Database] Successfully connected to {config.host}:{config.port}/{config.database}")
                    else:
                        raise Exception("Analytics database connection test failed")

        except Exception as e:
            error(f"[Analytics Database] Failed to initialize: {str(e)}")
            raise

    # Connection pool methods (get_connection, get_cursor, execute, execute_many,
    # fetch_all, fetch_one, close, __del__) inherited from BaseDatabaseManager


# Global database manager instances
db_manager = DatabaseManager()
analytics_db_manager = AnalyticsDatabaseManager()


def initialize_database(config: Dict[str, Any]) -> DatabaseManager:
    """Initialize the global credentials database manager.

    This initializes the credentials database (bots, accounts, encrypted_credentials).
    For analytics database initialization, use initialize_analytics_database().
    """
    # Use environment variables if DATABASE_URL is present, otherwise use config
    if os.environ.get("DATABASE_URL"):
        db_config = DatabaseConfig.from_env()
        info("[Credentials Database] Using DATABASE_URL from environment variables")
    else:
        db_config = DatabaseConfig.from_dict(config)
        info("[Credentials Database] Using database config from JSON configuration")

    db_manager.initialize(db_config)
    return db_manager


def initialize_analytics_database(config: Optional[Dict[str, Any]] = None) -> AnalyticsDatabaseManager:
    """Initialize the global analytics database manager.

    This initializes the analytics database (orders, trades, positions, balances).

    Args:
        config: Optional config dictionary. If not provided, uses environment variables.

    Returns:
        The initialized analytics database manager.
    """
    if config:
        analytics_config = AnalyticsDatabaseConfig.from_dict(config)
        info("[Analytics Database] Using database config from configuration")
    else:
        analytics_config = AnalyticsDatabaseConfig.from_env()
        analytics_db_url = os.environ.get("ANALYTICS_DATABASE_URL")
        if analytics_db_url:
            info("[Analytics Database] Using ANALYTICS_DATABASE_URL from environment variables")
        else:
            info("[Analytics Database] Falling back to DATABASE_URL (single database mode)")

    analytics_db_manager.initialize(analytics_config)
    return analytics_db_manager


def initialize_databases(
    credentials_config: Dict[str, Any], analytics_config: Optional[Dict[str, Any]] = None
) -> Tuple[DatabaseManager, AnalyticsDatabaseManager]:
    """Initialize both credentials and analytics databases.

    This is the recommended way to initialize dual databases for production.

    Args:
        credentials_config: Configuration for credentials database
        analytics_config: Optional configuration for analytics database. If not provided, uses environment variables.

    Returns:
        Tuple of (credentials_db_manager, analytics_db_manager)
    """
    credentials_mgr = initialize_database(credentials_config)
    analytics_mgr = initialize_analytics_database(analytics_config)
    info("[Database] Dual database initialization complete")
    return credentials_mgr, analytics_mgr


def get_db_manager() -> DatabaseManager:
    """Get the global credentials database manager instance."""
    return db_manager


def get_analytics_db_manager() -> AnalyticsDatabaseManager:
    """Get the global analytics database manager instance."""
    return analytics_db_manager
