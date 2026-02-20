#!/usr/bin/env python3
"""
Database migration runner for migration 024: Balance/Position Account Linking

Adds account_id foreign keys to account_balances and position_snapshots tables.
Run this script with DATABASE_URL environment variable pointing to production RDS.

Usage:
    export DATABASE_URL="postgresql://user:pass@rds-endpoint:5432/helena_bot"
    python src/database/migrations/run_migration_024.py
"""
import os
import sys

import psycopg

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def run_migration_024(database_url: str) -> None:
    """Run migration 024: Add account_id to balance and position tables.

    Args:
        database_url: PostgreSQL connection string

    Raises:
        Exception: If migration fails
    """
    print("=" * 80)
    print("Migration 024: Balance/Position Account Linking")
    print("=" * 80)

    try:
        # Connect to database with autocommit for DDL
        print("\nConnecting to database...")
        conn = psycopg.connect(database_url, autocommit=True)
        print("Connected successfully")

        # Read migration file
        migration_file = os.path.join(
            os.path.dirname(__file__),
            "scripts/024_update_balance_position_tables_for_account_linking.sql",
        )

        print(f"\n Reading migration file: {os.path.basename(migration_file)}")
        with open(migration_file, "r") as f:
            migration_sql = f.read()

        # Execute migration
        print("\nExecuting migration...")
        print("   (This will add account_id columns, rename columns, and create indexes)")

        with conn.cursor() as cursor:
            cursor.execute(migration_sql)

        print("Migration SQL executed successfully")

        # Verify account_balances table
        print("\nVerifying account_balances table...")
        with conn.cursor() as cursor:
            # Check for account_id column
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'account_balances'
                AND column_name IN ('account_id', 'asset', 'balance', 'usd_value', 'allocated', 'available')
                ORDER BY column_name;
            """
            )
            columns = cursor.fetchall()
            print(f"   Columns: {', '.join([c[0] for c in columns])}")

            # Check for indexes
            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'account_balances'
                AND indexname LIKE '%account%'
                ORDER BY indexname;
            """
            )
            indexes = cursor.fetchall()
            print(f"   Account indexes: {len(indexes)} found")

        # Verify position_snapshots table
        print("\nVerifying position_snapshots table...")
        with conn.cursor() as cursor:
            # Check for account_id column
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'position_snapshots'
                AND column_name = 'account_id';
            """
            )
            if cursor.fetchone():
                print("   account_id column exists")

            # Check for indexes
            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'position_snapshots'
                AND indexname LIKE '%account%'
                ORDER BY indexname;
            """
            )
            indexes = cursor.fetchall()
            print(f"   Account indexes: {len(indexes)} found")

        # Final verification
        print("\nMigration 024 completed successfully!")
        print("\nNext steps:")
        print("  1. Deploy new code via GitHub Actions")
        print("  2. Restart production bots")
        print("  3. Verify persistence logs")
        print("  4. Test API endpoints")

        conn.close()

    except FileNotFoundError as e:
        print(f"\nMigration file not found: {e}")
        print("   Make sure you're running from project root")
        sys.exit(1)

    except psycopg.Error as e:
        print(f"\nDatabase error: {e}")
        print("   Check DATABASE_URL and RDS connectivity")
        sys.exit(1)

    except Exception as e:
        print(f"\nMigration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print("\nDATABASE_URL environment variable not set")
        print("\nUsage:")
        print('  export DATABASE_URL="postgresql://user:pass@rds-host:5432/helena_bot"')
        print("  python src/database/migrations/run_migration_024.py")
        sys.exit(1)

    # Show connection info (hide password)
    safe_url = database_url.split("@")[1] if "@" in database_url else database_url
    print(f"\nTarget database: {safe_url}")
    print("=" * 80)

    # Confirm before running
    if os.environ.get("AUTO_CONFIRM") != "true":
        response = input("\nWARNING:  This will modify the production database. Continue? [y/N]: ")
        if response.lower() != "y":
            print("Migration cancelled")
            sys.exit(0)

    # Run migration
    run_migration_024(database_url)
