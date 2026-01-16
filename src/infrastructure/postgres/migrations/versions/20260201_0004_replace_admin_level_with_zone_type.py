"""Replace admin_level with zone_type in zones table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-01
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE zones ADD COLUMN zone_type VARCHAR(20)")
    op.execute("""
        UPDATE zones
        SET zone_type = CASE admin_level
            WHEN 2 THEN 'country'
            WHEN 4 THEN 'region'
            WHEN 6 THEN 'district'
            WHEN 8 THEN 'commune'
            WHEN 10 THEN 'fokontany'
            ELSE 'unknown'
        END
    """)
    op.execute("ALTER TABLE zones ALTER COLUMN zone_type SET NOT NULL")
    op.execute("DROP INDEX IF EXISTS idx_zones_admin_level")
    op.execute("ALTER TABLE zones DROP COLUMN admin_level")
    op.execute("CREATE INDEX idx_zones_zone_type ON zones (zone_type)")


def downgrade() -> None:
    op.execute("ALTER TABLE zones ADD COLUMN admin_level INT")
    op.execute("""
        UPDATE zones
        SET admin_level = CASE zone_type
            WHEN 'country' THEN 2
            WHEN 'region' THEN 4
            WHEN 'district' THEN 6
            WHEN 'commune' THEN 8
            WHEN 'fokontany' THEN 10
            ELSE NULL
        END
    """)
    op.execute("ALTER TABLE zones ALTER COLUMN admin_level SET NOT NULL")
    op.execute("DROP INDEX IF EXISTS idx_zones_zone_type")
    op.execute("ALTER TABLE zones DROP COLUMN zone_type")
    op.execute("CREATE INDEX idx_zones_admin_level ON zones (admin_level)")
