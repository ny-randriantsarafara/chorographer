"""Rename osm_id to id across all tables.

Revision ID: 0006
Revises: 0005
Create Date: 2026-01-22
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename osm_id to id in all tables
    # Note: Foreign keys need to be dropped and recreated
    
    # Drop foreign key constraint from segments table
    op.execute("ALTER TABLE segments DROP CONSTRAINT IF EXISTS segments_road_id_fkey")
    
    # Drop foreign key constraint from zones table
    op.execute("ALTER TABLE zones DROP CONSTRAINT IF EXISTS zones_parent_zone_id_fkey")
    
    # Rename columns
    op.execute("ALTER TABLE roads RENAME COLUMN osm_id TO id")
    op.execute("ALTER TABLE pois RENAME COLUMN osm_id TO id")
    op.execute("ALTER TABLE zones RENAME COLUMN osm_id TO id")
    
    # Recreate foreign key constraints with new column name
    op.execute("ALTER TABLE segments ADD CONSTRAINT segments_road_id_fkey FOREIGN KEY (road_id) REFERENCES roads(id)")
    op.execute("ALTER TABLE zones ADD CONSTRAINT zones_parent_zone_id_fkey FOREIGN KEY (parent_zone_id) REFERENCES zones(id) ON DELETE SET NULL")


def downgrade() -> None:
    # Drop foreign key constraints
    op.execute("ALTER TABLE segments DROP CONSTRAINT IF EXISTS segments_road_id_fkey")
    op.execute("ALTER TABLE zones DROP CONSTRAINT IF EXISTS zones_parent_zone_id_fkey")
    
    # Rename columns back
    op.execute("ALTER TABLE roads RENAME COLUMN id TO osm_id")
    op.execute("ALTER TABLE pois RENAME COLUMN id TO osm_id")
    op.execute("ALTER TABLE zones RENAME COLUMN id TO osm_id")
    
    # Recreate foreign key constraints with old column name
    op.execute("ALTER TABLE segments ADD CONSTRAINT segments_road_id_fkey FOREIGN KEY (road_id) REFERENCES roads(osm_id)")
    op.execute("ALTER TABLE zones ADD CONSTRAINT zones_parent_zone_id_fkey FOREIGN KEY (parent_zone_id) REFERENCES zones(osm_id) ON DELETE SET NULL")
