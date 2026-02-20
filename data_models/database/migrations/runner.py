#!/usr/bin/env python3
"""Database migration runner for Helena Bot."""

import argparse
import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from data_models.logging import error, info, setup_logging  # noqa: E402
from data_models.database.core.db_config import DatabaseConfig, DatabaseManager  # noqa: E402


class MigrationRunner:
    """Handles database migrations."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.db_manager = DatabaseManager()
        self.db_manager.initialize(config)

        # Create migrations tracking table
        self._create_migrations_table()

    def _create_migrations_table(self) -> None:
        """Create table to track applied migrations."""
        query = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        self.db_manager.execute(query)
        info("[MigrationRunner] Migrations table ready")

    def _get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations."""
        results = self.db_manager.fetch_all("SELECT version FROM schema_migrations ORDER BY version")
        return [r["version"] for r in results]

    def _mark_migration_applied(self, version: str) -> None:
        """Mark a migration as applied."""
        self.db_manager.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))

    def run_migrations(self, migrations_dir: Path) -> None:
        """Run all pending migrations."""
        # Get all migration files
        migration_files = sorted(migrations_dir.glob("*.sql"))
        if not migration_files:
            info("[MigrationRunner] No migration files found")
            return

        # Get applied migrations
        applied = set(self._get_applied_migrations())

        # Run pending migrations
        for migration_file in migration_files:
            version = migration_file.stem

            if version in applied:
                info(f"[MigrationRunner] Migration {version} already applied, skipping")
                continue

            info(f"[MigrationRunner] Running migration: {version}")

            try:
                # Read migration SQL
                with open(migration_file, "r") as f:
                    sql = f.read()

                # Execute migration
                with self.db_manager.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                        conn.commit()

                # Mark as applied
                self._mark_migration_applied(version)
                info(f"[MigrationRunner] Migration {version} completed successfully")

            except Exception as e:
                error(f"[MigrationRunner] Migration {version} failed: {str(e)}")
                raise

    def rollback_migration(self, version: str, migrations_dir: Path) -> None:
        """Rollback a specific migration (if rollback file exists)."""
        rollback_file = migrations_dir / f"{version}_rollback.sql"

        if not rollback_file.exists():
            error(f"[MigrationRunner] No rollback file found for version {version}")
            return

        info(f"[MigrationRunner] Rolling back migration: {version}")

        try:
            # Read rollback SQL
            with open(rollback_file, "r") as f:
                sql = f.read()

            # Execute rollback
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    conn.commit()

            # Remove from applied migrations
            self.db_manager.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))

            info(f"[MigrationRunner] Rollback of {version} completed successfully")

        except Exception as e:
            error(f"[MigrationRunner] Rollback of {version} failed: {str(e)}")
            raise

    def status(self) -> None:
        """Show migration status."""
        applied = self._get_applied_migrations()

        if not applied:
            print("No migrations applied yet")
        else:
            print("Applied migrations:")
            for version in applied:
                print(f"  - {version}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Helena Bot Database Migration Tool")
    parser.add_argument(
        "command",
        choices=["migrate", "rollback", "status"],
        help="Migration command to run",
    )
    parser.add_argument("--version", help="Migration version (for rollback)")
    parser.add_argument("--config", help="Config file path", default="config/main/config.json")
    parser.add_argument(
        "--env",
        action="store_true",
        help="Use environment variables for database config",
    )

    args = parser.parse_args()

    # Load database config
    if args.env:
        config = DatabaseConfig.from_env()
    else:
        # Load from config file
        import json

        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Config file not found: {config_path}")
            sys.exit(1)

        with open(config_path) as f:
            full_config = json.load(f)
            db_config = full_config.get("database", {})
            config = DatabaseConfig.from_dict(db_config)

    # Set up logging
    setup_logging(log_level="INFO")

    # Get migrations directory
    migrations_dir = Path(__file__).parent / "scripts"

    # Create runner
    runner = MigrationRunner(config)

    # Execute command
    try:
        if args.command == "migrate":
            runner.run_migrations(migrations_dir)
        elif args.command == "rollback":
            if not args.version:
                print("Version required for rollback")
                sys.exit(1)
            runner.rollback_migration(args.version, migrations_dir)
        elif args.command == "status":
            runner.status()
    except Exception as e:
        error(f"[MigrationRunner] Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        runner.db_manager.close()


if __name__ == "__main__":
    main()
