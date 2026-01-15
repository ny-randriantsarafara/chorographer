"""Add segments table for routing graph.

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-01
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE segments (
            id BIGINT PRIMARY KEY,
            road_id BIGINT NOT NULL REFERENCES roads(osm_id),
            geometry GEOMETRY(LineString, 4326) NOT NULL,
            start_point GEOMETRY(Point, 4326) NOT NULL,
            end_point GEOMETRY(Point, 4326) NOT NULL,
            length DOUBLE PRECISION NOT NULL,
            surface_factor DOUBLE PRECISION NOT NULL,
            smoothness_factor DOUBLE PRECISION NOT NULL,
            rainy_season_factor DOUBLE PRECISION NOT NULL,
            oneway BOOLEAN NOT NULL,
            base_speed INT NOT NULL,
            effective_speed_kmh DOUBLE PRECISION NOT NULL,
            travel_time_seconds DOUBLE PRECISION NOT NULL,
            cost DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX idx_segments_geometry ON segments USING GIST (geometry)")
    op.execute("CREATE INDEX idx_segments_road_id ON segments (road_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS segments CASCADE")
