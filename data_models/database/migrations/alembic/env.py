"""Alembic migration environment configuration for Helena Bot Core.

This module configures the Alembic environment for database migrations.
It imports all SQLAlchemy models so Alembic can auto-detect schema changes.

For production migrations using raw SQL (op.execute), set ALEMBIC_MINIMAL=1
to skip model imports and avoid dependency issues.
"""

import os
import sys
from logging.config import fileConfig
from typing import Optional

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# Import models only if not in minimal mode (for autogenerate support)
# Production migrations using raw SQL can skip this with ALEMBIC_MINIMAL=1
if not os.environ.get("ALEMBIC_MINIMAL"):
    pass

    # Import all database models so Alembic can detect them
    from data_models.database.tables.base import Base

    target_metadata = Base.metadata
else:
    # Minimal mode: no model imports, no autogenerate
    # Used for production migrations that use raw SQL via op.execute()
    target_metadata = None

# Alembic Config object provides access to the .ini file
config = context.config

# Interpret the config file for Python logging (if available)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url() -> Optional[str]:
    """Get database URL from environment variable.

    Supports dual-database architecture:
    - ANALYTICS_DATABASE_URL: For high-volume data (chat, trades, orders)
    - DATABASE_URL: For operational data (bots, accounts, credentials)

    For chat persistence (migration 031+), uses ANALYTICS_DATABASE_URL.

    Returns:
        Optional[str]: PostgreSQL connection string from environment
    """
    # Check for analytics database first (chat tables, trades, orders)
    analytics_url = os.environ.get("ANALYTICS_DATABASE_URL")
    if analytics_url:
        return analytics_url

    # Fallback to credentials database
    return os.environ.get("DATABASE_URL")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is also acceptable. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate
    a connection with the context.
    """
    # Override sqlalchemy.url with DATABASE_URL from environment
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}
    db_url = get_url()
    if db_url:
        configuration["sqlalchemy.url"] = db_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
