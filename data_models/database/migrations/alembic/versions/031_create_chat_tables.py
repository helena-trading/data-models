"""Create chat persistence tables

Creates three tables for chat conversation persistence:
1. chat_conversations - Stores conversation metadata and AI summaries
2. chat_messages - Stores individual messages with tool execution data
3. chat_user_preferences - Stores user-specific chat settings

Includes PostgreSQL full-text search indexes and auto-update triggers.

Revision ID: 031
Revises: 030
Create Date: 2025-10-29 00:00:00.000000

"""

import os
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create chat persistence tables with indexes and triggers."""

    # Read the SQL migration file
    sql_file_path = os.path.join(os.path.dirname(__file__), "../../scripts/031_create_chat_tables.sql")

    with open(sql_file_path, "r") as f:
        migration_sql = f.read()

    # Execute the migration
    op.execute(migration_sql)


def downgrade() -> None:
    """Drop chat persistence tables and related objects."""

    # Drop tables in reverse order (respecting foreign key constraints)
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS chat_conversations CASCADE;")
    op.execute("DROP TABLE IF EXISTS chat_user_preferences CASCADE;")

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS chat_conversations_updated_at_trigger ON chat_conversations;")
    op.execute("DROP TRIGGER IF EXISTS chat_user_preferences_updated_at_trigger ON chat_user_preferences;")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_chat_conversations_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS update_chat_user_preferences_updated_at();")
