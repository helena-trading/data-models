#!/usr/bin/env python3
"""
Database migration runner for migration 025: Private Data Hub tables.

Creates:
- private_data_hubs
- private_data_hub_accounts
"""

import os
import sys

import psycopg

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def run_migration_025(database_url: str) -> None:
    """Run migration 025."""
    print("=" * 80)
    print("Migration 025: Private Data Hub Tables")
    print("=" * 80)

    try:
        print("\nConnecting to database...")
        conn = psycopg.connect(database_url, autocommit=True)
        print("Connected successfully")

        migration_file = os.path.join(
            os.path.dirname(__file__),
            "scripts/025_create_private_data_hub_tables.sql",
        )

        print(f"\nReading migration file: {os.path.basename(migration_file)}")
        with open(migration_file, "r", encoding="utf-8") as file:
            migration_sql = file.read()

        print("\nExecuting migration...")
        with conn.cursor() as cursor:
            cursor.execute(migration_sql)

        print("Migration SQL executed successfully")

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('private_data_hubs', 'private_data_hub_accounts')
                ORDER BY table_name;
                """
            )
            tables = [row[0] for row in cursor.fetchall()]
            print(f"\nVerified tables: {', '.join(tables)}")

        conn.close()
        print("\nMigration 025 completed successfully")
    except Exception as exc:
        print(f"\nMigration failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable not set")
        sys.exit(1)

    safe_url = database_url.split("@")[1] if "@" in database_url else database_url
    print(f"Target database: {safe_url}")

    if os.environ.get("AUTO_CONFIRM") != "true":
        response = input("\nWARNING: This will modify the database. Continue? [y/N]: ")
        if response.lower() != "y":
            print("Migration cancelled")
            sys.exit(0)

    run_migration_025(database_url)
