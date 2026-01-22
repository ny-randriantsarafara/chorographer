"""Remove malagasy_name column from zones table.

Revision ID: 0007
Revises: 0006
Create Date: 2026-01-22
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove malagasy_name column - name:mg will still be in tags JSONB if needed
    op.execute("ALTER TABLE zones DROP COLUMN IF EXISTS malagasy_name")


def downgrade() -> None:
    # Add back malagasy_name column
    op.execute("ALTER TABLE zones ADD COLUMN malagasy_name TEXT")
