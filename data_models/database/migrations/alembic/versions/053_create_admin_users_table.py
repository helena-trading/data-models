"""Create admin_users table for dashboard authentication

Revision ID: 053
Revises: 052
Create Date: 2026-02-03

Adds admin_users table to the credentials database for server-side
dashboard authentication with bcrypt-hashed passwords.

Seeds a default 'admin' user with a pre-computed bcrypt hash.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "053"
down_revision: Union[str, None] = "052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Pre-computed bcrypt hash — no runtime bcrypt dependency needed
_ADMIN_PASSWORD_HASH = "$2b$12$awO6DI0XboFU8RCxAsiRauM.NJaMHqGZTr7Os.ZI1Y7uh82wwLrA6"


def upgrade() -> None:
    """Create admin_users table and seed default admin user."""

    # Create the table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            last_login_at TIMESTAMPTZ
        );
        """
    )

    # Create index on username
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_users_username
        ON admin_users (username);
        """
    )

    # Ensure is_active has a database-level default
    # (Base.metadata.create_all may have created the table without it)
    op.execute(
        """
        ALTER TABLE admin_users ALTER COLUMN is_active SET DEFAULT TRUE;
        """
    )

    # Seed default admin user (only if none exists yet)
    op.execute(
        f"""
        INSERT INTO admin_users (username, password_hash, is_active)
        SELECT 'admin', '{_ADMIN_PASSWORD_HASH}', TRUE
        WHERE NOT EXISTS (SELECT 1 FROM admin_users WHERE username = 'admin');
        """
    )


def downgrade() -> None:
    """Drop admin_users table."""

    op.execute(
        """
        DROP INDEX IF EXISTS idx_admin_users_username;
        """
    )

    op.execute(
        """
        DROP TABLE IF EXISTS admin_users;
        """
    )
