"""Add derived fields for roads, POIs, and zones.

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-01
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE roads
            ADD COLUMN length DOUBLE PRECISION,
            ADD COLUMN surface_factor DOUBLE PRECISION,
            ADD COLUMN smoothness_factor DOUBLE PRECISION,
            ADD COLUMN effective_speed_kmh INT,
            ADD COLUMN penalized_speed_kmh DOUBLE PRECISION
    """)

    op.execute("""
        ALTER TABLE pois
            ADD COLUMN is_24_7 BOOLEAN,
            ADD COLUMN formatted_address TEXT
    """)

    op.execute("""
        ALTER TABLE zones
            ADD COLUMN area DOUBLE PRECISION,
            ADD COLUMN centroid GEOMETRY(Point, 4326)
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE zones
            DROP COLUMN IF EXISTS centroid,
            DROP COLUMN IF EXISTS area
    """)

    op.execute("""
        ALTER TABLE pois
            DROP COLUMN IF EXISTS formatted_address,
            DROP COLUMN IF EXISTS is_24_7
    """)

    op.execute("""
        ALTER TABLE roads
            DROP COLUMN IF EXISTS penalized_speed_kmh,
            DROP COLUMN IF EXISTS effective_speed_kmh,
            DROP COLUMN IF EXISTS smoothness_factor,
            DROP COLUMN IF EXISTS surface_factor,
            DROP COLUMN IF EXISTS length
    """)
