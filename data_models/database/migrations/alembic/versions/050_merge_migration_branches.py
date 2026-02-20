"""Merge parallel migration branches

This migration merges two parallel branches that diverged from revision 040:
- Branch 1: 040 → 041 → 042 → ... → 049 (numeric sequence)
- Branch 2: 040 → c6a8e8b82ba9 (error_logs enhancement)

The divergence occurred when c6a8e8b82ba9 was created with UUID revision
instead of following the numeric sequence.

Revision ID: 050
Revises: 049, c6a8e8b82ba9
Create Date: 2026-01-06

"""

from typing import Sequence, Tuple, Union

# revision identifiers, used by Alembic.
revision: str = "050"
down_revision: Tuple[str, str] = ("049", "c6a8e8b82ba9")  # Merge point
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No operations needed - this is a merge point."""
    pass


def downgrade() -> None:
    """No operations needed - this is a merge point."""
    pass
