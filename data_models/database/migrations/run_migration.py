#!/usr/bin/env python3
"""
Database migration runner for bot_parameters table
"""
import os
import sys

import psycopg

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from data_models.logging import info as Log


def run_migration(database_url: str) -> None:
    """Run the bot_parameters migration"""
    try:
        # Parse database URL
        # Format: postgresql://user:password@host:port/database
        parts = database_url.replace("postgresql://", "").split("@")
        user_pass = parts[0].split(":")
        host_port_db = parts[1].split("/")
        host_port = host_port_db[0].split(":")

        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ""
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else "5432"
        database = host_port_db[1]

        # Connect to database
        Log(f"Connecting to database {database} at {host}:{port}")
        conninfo = f"host={host} port={port} dbname={database} user={user} password={password}"
        conn = psycopg.connect(conninfo, autocommit=True)

        # Read migration file
        migration_file = os.path.join(os.path.dirname(__file__), "002_create_bot_parameters.sql")
        with open(migration_file, "r") as f:
            migration_sql = f.read()

        # Execute migration
        with conn.cursor() as cursor:
            Log("Executing bot_parameters migration...")
            cursor.execute(migration_sql)
            Log("Migration completed successfully!")

            # Verify tables were created
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('bot_parameters', 'bot_parameters_history')
                ORDER BY table_name;
            """
            )

            tables = cursor.fetchall()
            Log(f"Created tables: {[t[0] for t in tables]}")

            # Check parameter count
            cursor.execute("SELECT COUNT(*) FROM bot_parameters;")
            result = cursor.fetchone()
            count = result[0] if result else 0
            Log(f"Initialized {count} parameters")

        conn.close()

    except Exception as e:
        Log(f"Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    # Get database URL from environment or use default
    database_url = os.environ.get("DATABASE_URL", "postgresql://helena:helena123@localhost:5432/helena_bot")

    # Run migration
    run_migration(database_url)
