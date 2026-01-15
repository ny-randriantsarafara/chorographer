"""Initial schema with roads, pois, and zones tables.

Revision ID: 0001
Revises:
Create Date: 2026-01-15
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Roads table
    op.execute("""
        CREATE TABLE roads (
            osm_id BIGINT PRIMARY KEY,
            geometry GEOMETRY(LineString, 4326) NOT NULL,
            road_type VARCHAR(50) NOT NULL,
            surface VARCHAR(50),
            smoothness VARCHAR(50),
            name TEXT,
            lanes INT DEFAULT 2,
            oneway BOOLEAN DEFAULT FALSE,
            max_speed INT,
            tags JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # POIs table
    op.execute("""
        CREATE TABLE pois (
            osm_id BIGINT PRIMARY KEY,
            geometry GEOMETRY(Point, 4326) NOT NULL,
            category VARCHAR(50) NOT NULL,
            subcategory VARCHAR(100),
            name TEXT,
            address JSONB,
            phone TEXT,
            opening_hours TEXT,
            price_range INT,
            website TEXT,
            tags JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Zones table
    op.execute("""
        CREATE TABLE zones (
            osm_id BIGINT PRIMARY KEY,
            geometry GEOMETRY(Polygon, 4326) NOT NULL,
            admin_level INT NOT NULL,
            name TEXT NOT NULL,
            malagasy_name TEXT,
            iso_code VARCHAR(10),
            population INT,
            tags JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Spatial indexes (GIST)
    op.execute("CREATE INDEX idx_roads_geometry ON roads USING GIST (geometry)")
    op.execute("CREATE INDEX idx_pois_geometry ON pois USING GIST (geometry)")
    op.execute("CREATE INDEX idx_zones_geometry ON zones USING GIST (geometry)")

    # Other useful indexes
    op.execute("CREATE INDEX idx_roads_road_type ON roads (road_type)")
    op.execute("CREATE INDEX idx_roads_surface ON roads (surface)")
    op.execute("CREATE INDEX idx_pois_category ON pois (category)")
    op.execute("CREATE INDEX idx_pois_subcategory ON pois (subcategory)")
    op.execute("CREATE INDEX idx_zones_admin_level ON zones (admin_level)")
    op.execute("CREATE INDEX idx_zones_name ON zones (name)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS zones CASCADE")
    op.execute("DROP TABLE IF EXISTS pois CASCADE")
    op.execute("DROP TABLE IF EXISTS roads CASCADE")
    op.execute("DROP EXTENSION IF EXISTS postgis")
