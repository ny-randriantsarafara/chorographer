"""Add search fields to POIs and hierarchy fields to Zones.

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-22
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add POI search fields
    op.execute("""
        ALTER TABLE pois
            ADD COLUMN name_normalized TEXT,
            ADD COLUMN search_text TEXT,
            ADD COLUMN search_text_normalized TEXT,
            ADD COLUMN has_name BOOLEAN DEFAULT FALSE,
            ADD COLUMN popularity INT DEFAULT 0
    """)
    
    # Populate has_name based on existing name values
    op.execute("""
        UPDATE pois
        SET has_name = (name IS NOT NULL AND name != '')
    """)
    
    # Create a function to normalize text (lowercase, trim, remove extra spaces)
    op.execute("""
        CREATE OR REPLACE FUNCTION normalize_text(text) RETURNS TEXT AS $$
            SELECT LOWER(TRIM(REGEXP_REPLACE($1, '\\s+', ' ', 'g')))
        $$ LANGUAGE SQL IMMUTABLE
    """)
    
    # Populate name_normalized for existing records
    op.execute("""
        UPDATE pois
        SET name_normalized = normalize_text(name)
        WHERE name IS NOT NULL
    """)
    
    # Create a function to build search text from POI fields
    op.execute("""
        CREATE OR REPLACE FUNCTION build_poi_search_text(
            p_name TEXT,
            p_tags JSONB
        ) RETURNS TEXT AS $$
        DECLARE
            result TEXT;
            brand TEXT;
            operator TEXT;
            old_name TEXT;
        BEGIN
            -- Start with name if available
            result := COALESCE(p_name, '');
            
            -- Add brand from tags
            brand := p_tags->>'brand';
            IF brand IS NOT NULL AND brand != '' THEN
                result := CONCAT_WS(' ', result, brand);
            END IF;
            
            -- Add operator from tags
            operator := p_tags->>'operator';
            IF operator IS NOT NULL AND operator != '' THEN
                result := CONCAT_WS(' ', result, operator);
            END IF;
            
            -- Add old_name from tags
            old_name := p_tags->>'old_name';
            IF old_name IS NOT NULL AND old_name != '' THEN
                result := CONCAT_WS(' ', result, old_name);
            END IF;
            
            -- If still empty, use subcategory or category from tags
            IF result = '' THEN
                result := COALESCE(
                    p_tags->>'amenity',
                    p_tags->>'shop',
                    p_tags->>'tourism',
                    'unknown'
                );
            END IF;
            
            RETURN TRIM(result);
        END;
        $$ LANGUAGE plpgsql IMMUTABLE
    """)
    
    # Populate search_text for existing records
    op.execute("""
        UPDATE pois
        SET search_text = build_poi_search_text(name, tags)
    """)
    
    # Populate search_text_normalized
    op.execute("""
        UPDATE pois
        SET search_text_normalized = normalize_text(search_text)
        WHERE search_text IS NOT NULL
    """)
    
    # Enable pg_trgm extension for fuzzy text search (must be before GIN index)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    
    # Create indexes for search fields
    op.execute("CREATE INDEX idx_pois_has_name ON pois (has_name)")
    op.execute("CREATE INDEX idx_pois_search_text_normalized ON pois USING GIN (search_text_normalized gin_trgm_ops)")
    op.execute("CREATE INDEX idx_pois_popularity ON pois (popularity DESC)")
    
    # Add Zone hierarchy fields
    op.execute("""
        ALTER TABLE zones
            ADD COLUMN level INT,
            ADD COLUMN parent_zone_id BIGINT REFERENCES zones(osm_id) ON DELETE SET NULL
    """)
    
    # Populate level based on zone_type
    op.execute("""
        UPDATE zones
        SET level = CASE zone_type
            WHEN 'country' THEN 0
            WHEN 'region' THEN 1
            WHEN 'district' THEN 2
            WHEN 'commune' THEN 3
            WHEN 'fokontany' THEN 4
            ELSE 99
        END
    """)
    
    # Make level NOT NULL after populating
    op.execute("ALTER TABLE zones ALTER COLUMN level SET NOT NULL")
    
    # Update geometry column to support MultiPolygon as well as Polygon
    # First, change the column type constraint to allow both
    op.execute("ALTER TABLE zones ALTER COLUMN geometry TYPE GEOMETRY(Geometry, 4326) USING geometry")
    
    # Then convert any Polygons to MultiPolygons
    op.execute("""
        UPDATE zones
        SET geometry = ST_Multi(geometry)
        WHERE GeometryType(geometry) = 'POLYGON'
    """)
    
    # Finally, set the type to MultiPolygon
    op.execute("ALTER TABLE zones ALTER COLUMN geometry TYPE GEOMETRY(MultiPolygon, 4326) USING geometry")
    
    # Create indexes for hierarchy
    op.execute("CREATE INDEX idx_zones_level ON zones (level)")
    op.execute("CREATE INDEX idx_zones_parent_zone_id ON zones (parent_zone_id)")


def downgrade() -> None:
    # Remove Zone hierarchy fields
    op.execute("DROP INDEX IF EXISTS idx_zones_parent_zone_id")
    op.execute("DROP INDEX IF EXISTS idx_zones_level")
    op.execute("ALTER TABLE zones ALTER COLUMN geometry TYPE GEOMETRY(Polygon, 4326)")
    op.execute("""
        ALTER TABLE zones
            DROP COLUMN IF EXISTS parent_zone_id,
            DROP COLUMN IF EXISTS level
    """)
    
    # Remove POI search fields
    op.execute("DROP INDEX IF EXISTS idx_pois_popularity")
    op.execute("DROP INDEX IF EXISTS idx_pois_search_text_normalized")
    op.execute("DROP INDEX IF EXISTS idx_pois_has_name")
    op.execute("DROP FUNCTION IF EXISTS build_poi_search_text(TEXT, JSONB)")
    op.execute("DROP FUNCTION IF EXISTS normalize_text(TEXT)")
    op.execute("""
        ALTER TABLE pois
            DROP COLUMN IF EXISTS popularity,
            DROP COLUMN IF EXISTS has_name,
            DROP COLUMN IF EXISTS search_text_normalized,
            DROP COLUMN IF EXISTS search_text,
            DROP COLUMN IF EXISTS name_normalized
    """)
