# PostgreSQL Component

## What is the PostgreSQL Component?

The PostgreSQL Component saves geographic data to a PostgreSQL database with PostGIS extension. It takes Domain entities (Roads, POIs, Zones) and stores them in database tables where they can be:
- Queried efficiently
- Analyzed spatially
- Used by other applications
- Persisted long-term

Think of it as the **filing cabinet** where we organize and store all the map data.

## Why PostgreSQL with PostGIS?

### PostgreSQL
A powerful, reliable open-source database that:
- Handles millions of records
- Supports complex queries
- Has excellent tools and documentation
- Is free and widely used

### PostGIS
An extension for PostgreSQL that adds support for:
- Geographic objects (points, lines, polygons)
- Spatial indexes (find things nearby quickly)
- Geographic calculations (distances, areas, intersections)
- Map coordinate systems

Together, they're the industry standard for storing map data.

## The Files

```
infrastructure/postgres/
├── connection.py       # Manages database connections
├── writer.py          # Saves entities to database
└── migrations/        # Database schema management
    ├── alembic.ini    # Alembic configuration
    ├── env.py         # Migration environment
    ├── script.py.mako # Migration template
    └── versions/      # Individual migration files
        └── 20260115_0001_initial_schema.py
```

---

## Component 1: Connection Management

**Purpose:** Create and manage connections to the PostgreSQL database.

### Why Connection Pooling?

Creating a new database connection is slow (can take 100+ milliseconds). Connection pooling:
1. Creates several connections at startup
2. Reuses them for multiple operations
3. Much faster (microseconds instead of milliseconds)

Think of it like a taxi stand:
- ❌ Without pooling: Call a taxi, wait for it, use it, it leaves. Repeat every time.
- ✅ With pooling: Taxis wait at the stand, take one when needed, it returns when done.

### The Connection Pool

```python
from psycopg_pool import AsyncConnectionPool
from infrastructure.config import Settings

async def create_pool(settings: Settings) -> AsyncConnectionPool:
    """
    Create an async connection pool.
    
    Args:
        settings: Configuration with database credentials
    
    Returns:
        Connection pool ready to use
    """
    # Build connection string
    conninfo = (
        f"host={settings.POSTGRES_HOST} "
        f"port={settings.POSTGRES_PORT} "
        f"dbname={settings.POSTGRES_DB} "
        f"user={settings.POSTGRES_USER} "
        f"password={settings.POSTGRES_PASSWORD}"
    )
    
    # Create pool with:
    # - min_size: Always keep this many connections open
    # - max_size: Never exceed this many connections
    pool = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=2,   # Always have 2 connections ready
        max_size=10,  # Maximum 10 concurrent connections
        open=False
    )
    
    # Open the pool (connect to database)
    await pool.open()
    
    return pool
```

### Using the Pool

```python
# Create pool once at startup
pool = await create_pool(settings)

# Use it many times
async with pool.connection() as conn:
    # Do database work
    await conn.execute("INSERT INTO ...")

# The connection automatically returns to the pool
```

### Closing the Pool

```python
# When application shuts down
await pool.close()
```

---

## Component 2: PostgresWriter

**Purpose:** Implement the GeoRepository port - save Domain entities to the database.

### What It Does

1. Receives batches of Domain entities
2. Converts them to SQL INSERT/UPDATE statements
3. Executes statements efficiently
4. Handles conflicts (updates existing records)

### The Writer Class

```python
from typing import List
from psycopg_pool import AsyncConnectionPool
from application.ports import GeoRepository
from domain.entities import Road, POI, Zone

class PostgresWriter(GeoRepository):
    """
    Saves geographic entities to PostgreSQL.
    
    Implements the GeoRepository port from Application layer.
    """
    
    def __init__(self, pool: AsyncConnectionPool, batch_size: int = 1000):
        """
        Initialize the writer.
        
        Args:
            pool: Database connection pool
            batch_size: How many records to insert at once
        """
        self.pool = pool
        self.batch_size = batch_size
    
    async def save_roads(self, roads: List[Road]) -> None:
        """
        Save roads to the database.
        
        Args:
            roads: List of Road entities to save
        """
        if not roads:
            return
        
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                # Prepare data for batch insert
                values = [
                    self._road_to_db_row(road)
                    for road in roads
                ]
                
                # Execute batch insert
                await cur.executemany(
                    """
                    INSERT INTO roads (
                        id, geometry, road_type, surface,
                        smoothness, name, lanes, oneway, max_speed, tags
                    ) VALUES (
                        %s, ST_GeomFromText(%s, 4326), %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        geometry = EXCLUDED.geometry,
                        road_type = EXCLUDED.road_type,
                        surface = EXCLUDED.surface,
                        smoothness = EXCLUDED.smoothness,
                        name = EXCLUDED.name,
                        lanes = EXCLUDED.lanes,
                        oneway = EXCLUDED.oneway,
                        max_speed = EXCLUDED.max_speed,
                        tags = EXCLUDED.tags,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    values
                )
                
                # Commit the transaction
                await conn.commit()
    
    def _road_to_db_row(self, road: Road) -> tuple:
        """
        Convert Road entity to database row.
        
        Returns:
            Tuple of values matching the INSERT statement
        """
        # Convert geometry to WKT (Well-Known Text)
        # Format: LINESTRING(lon1 lat1, lon2 lat2, ...)
        coords_str = ", ".join(
            f"{coord.lon} {coord.lat}"
            for coord in road.geometry
        )
        wkt = f"LINESTRING({coords_str})"
        
        return (
            road.id,
            wkt,  # PostGIS will convert this to geometry
            road.road_type.value,
            road.surface.value,
            road.smoothness.value,
            road.name,
            road.lanes,
            road.oneway,
            road.max_speed,
            road.tags  # PostgreSQL automatically converts dict to JSONB
        )
```

### Key Concepts

#### WKT (Well-Known Text)

A standard text format for geometric shapes:

```python
# Point
"POINT(47.5079 -18.8792)"

# LineString (road)
"LINESTRING(47.5079 -18.8792, 47.5090 -18.8800, 47.5100 -18.8810)"

# Polygon (zone)
"POLYGON((47.3 -18.7, 47.7 -18.7, 47.7 -19.1, 47.3 -19.1, 47.3 -18.7))"
```

PostGIS function `ST_GeomFromText` converts this to an internal geometry format.

#### SRID (Spatial Reference System Identifier)

The number 4326 means "WGS84" - the standard GPS coordinate system:
- Latitude: -90 to +90
- Longitude: -180 to +180

#### ON CONFLICT DO UPDATE (Upsert)

```sql
INSERT INTO roads (...) VALUES (...)
ON CONFLICT (id) DO UPDATE SET ...
```

This means:
- Try to insert the road
- If a road with this id already exists, update it instead
- This is called an "upsert" (insert or update)

Useful when re-importing OSM data - we update existing roads instead of failing.

### Saving POIs

```python
async def save_pois(self, pois: List[POI]) -> None:
    """Save POIs to the database."""
    if not pois:
        return
    
    async with self.pool.connection() as conn:
        async with conn.cursor() as cur:
            values = [self._poi_to_db_row(poi) for poi in pois]
            
            await cur.executemany(
                """
                INSERT INTO pois (
                    id, geometry, category, subcategory,
                    name, address, phone, opening_hours,
                    price_range, website,
                    name_normalized, search_text, search_text_normalized,
                    has_name, popularity, tags
                ) VALUES (
                    %s, ST_GeomFromText(%s, 4326), %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    geometry = EXCLUDED.geometry,
                    category = EXCLUDED.category,
                    subcategory = EXCLUDED.subcategory,
                    name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    phone = EXCLUDED.phone,
                    opening_hours = EXCLUDED.opening_hours,
                    price_range = EXCLUDED.price_range,
                    website = EXCLUDED.website,
                    name_normalized = EXCLUDED.name_normalized,
                    search_text = EXCLUDED.search_text,
                    search_text_normalized = EXCLUDED.search_text_normalized,
                    has_name = EXCLUDED.has_name,
                    popularity = EXCLUDED.popularity,
                    tags = EXCLUDED.tags,
                    updated_at = CURRENT_TIMESTAMP
                """,
                values
            )
            await conn.commit()

def _poi_to_db_row(self, poi: POI) -> tuple:
    """Convert POI entity to database row."""
    # POI geometry is a point
    wkt = f"POINT({poi.coordinates.lon} {poi.coordinates.lat})"
    
    # Convert address to JSONB if present
    address_json = None
    if poi.address:
        address_json = {
            "street": poi.address.street,
            "housenumber": poi.address.housenumber,
            "city": poi.address.city,
            "postcode": poi.address.postcode,
        }
    
    return (
        poi.id,
        wkt,
        poi.category.value,
        poi.subcategory,
        poi.name,
        address_json,
        poi.phone,
        poi.opening_hours,
        poi.price_range,
        poi.website,
        poi.name_normalized,
        poi.search_text,
        poi.search_text_normalized,
        poi.has_name,
        poi.popularity,
        poi.tags
    )
```

### Saving Zones

```python
async def save_zones(self, zones: List[Zone]) -> None:
    """Save zones to the database."""
    if not zones:
        return
    
    async with self.pool.connection() as conn:
        async with conn.cursor() as cur:
            values = [self._zone_to_db_row(zone) for zone in zones]
            
            await cur.executemany(
                """
                INSERT INTO zones (
                    id, geometry, zone_type, name,
                    level, parent_zone_id, iso_code, population, tags
                ) VALUES (
                    %s, ST_Multi(ST_GeomFromText(%s, 4326)), %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    geometry = EXCLUDED.geometry,
                    zone_type = EXCLUDED.zone_type,
                    name = EXCLUDED.name,
                    level = EXCLUDED.level,
                    parent_zone_id = EXCLUDED.parent_zone_id,
                    iso_code = EXCLUDED.iso_code,
                    population = EXCLUDED.population,
                    tags = EXCLUDED.tags,
                    updated_at = CURRENT_TIMESTAMP
                """,
                values
            )
            await conn.commit()

def _zone_to_db_row(self, zone: Zone) -> tuple:
    """Convert Zone entity to database row."""
    # Zone geometry is a polygon
    coords_str = ", ".join(
        f"{coord.lon} {coord.lat}"
        for coord in zone.geometry
    )
    wkt = f"POLYGON(({coords_str}))"
    
    return (
        zone.id,
        wkt,
        zone.zone_type,
        zone.name,
        zone.level,
        zone.parent_zone_id,
        zone.iso_code,
        zone.population,
        zone.tags
    )
```

---

## Component 3: Database Migrations

**Purpose:** Manage database schema changes over time.

### What are Migrations?

Migrations are version-controlled changes to the database structure:
- Create tables
- Add columns
- Create indexes
- Modify data types

Each migration has:
- **Upgrade**: Apply the change
- **Downgrade**: Undo the change

### Why Use Migrations?

Instead of manually running SQL scripts:
```bash
# ❌ Manual (error-prone)
psql -d lemurion -f create_tables.sql
```

Use migrations:
```bash
# ✅ Automated (tracked, repeatable)
alembic upgrade head
```

Benefits:
- Version control for database schema
- Can apply changes incrementally
- Can rollback if something goes wrong
- Team members get same schema automatically

### Base Schema Migration

```python
# migrations/versions/20260115_0001_initial_schema.py
"""
Base database schema (shown with current column names).

Creates tables for roads, pois, and zones.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# Revision identifiers
revision = '20260115_0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """
    Create initial tables.
    """
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    
    # Create roads table
    op.create_table(
        'roads',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('geometry', sa.String, nullable=False),  # PostGIS GEOMETRY
        sa.Column('road_type', sa.String(50), nullable=False),
        sa.Column('surface', sa.String(50), nullable=False),
        sa.Column('smoothness', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('lanes', sa.Integer, default=2),
        sa.Column('oneway', sa.Boolean, default=False),
        sa.Column('max_speed', sa.Integer, nullable=True),
        sa.Column('tags', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Convert geometry column to PostGIS type
    op.execute(
        "ALTER TABLE roads ALTER COLUMN geometry "
        "TYPE geometry(LINESTRING, 4326) USING geometry::geometry"
    )
    
    # Create spatial index for fast geographic queries
    op.execute(
        "CREATE INDEX idx_roads_geometry "
        "ON roads USING GIST (geometry)"
    )
    
    # Create POIs table
    op.create_table(
        'pois',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('geometry', sa.String, nullable=False),  # PostGIS GEOMETRY
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('subcategory', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('address', JSONB, nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('opening_hours', sa.String(255), nullable=True),
        sa.Column('price_range', sa.Integer, nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('tags', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now())
    )
    
    op.execute(
        "ALTER TABLE pois ALTER COLUMN geometry "
        "TYPE geometry(POINT, 4326) USING geometry::geometry"
    )
    
    op.execute(
        "CREATE INDEX idx_pois_geometry "
        "ON pois USING GIST (geometry)"
    )
    
    # Create zones table
    op.create_table(
        'zones',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('geometry', sa.String, nullable=False),  # PostGIS GEOMETRY
        sa.Column('zone_type', sa.String(20), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('level', sa.Integer, nullable=False),
        sa.Column('parent_zone_id', sa.BigInteger, nullable=True),
        sa.Column('iso_code', sa.String(10), nullable=True),
        sa.Column('population', sa.Integer, nullable=True),
        sa.Column('tags', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now())
    )
    
    op.execute(
        "ALTER TABLE zones ALTER COLUMN geometry "
        "TYPE geometry(POLYGON, 4326) USING geometry::geometry"
    )
    
    op.execute(
        "CREATE INDEX idx_zones_geometry "
        "ON zones USING GIST (geometry)"
    )

def downgrade():
    """
    Undo initial tables.
    """
    op.drop_table('zones')
    op.drop_table('pois')
    op.drop_table('roads')
```

Later migrations add POI search fields, zone hierarchy indexes, and update zone geometry to MultiPolygon.

### Running Migrations

```bash
# Navigate to migrations directory
cd src/infrastructure/postgres/migrations

# Apply all pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# See migration history
alembic history

# Check current version
alembic current
```

### Creating New Migrations

```bash
# Create a new migration
alembic revision -m "add_segments_table"

# This creates a new file in versions/
# Edit it to add your schema changes

# Apply it
alembic upgrade head
```

---

## Spatial Indexes (GIST)

### What are They?

Spatial indexes make geographic queries fast:

```sql
-- Without index: Check every row (slow)
SELECT * FROM pois WHERE ST_Distance(geometry, point) < 1000;

-- With GIST index: Only check nearby rows (fast)
```

### Creating Spatial Indexes

```sql
CREATE INDEX idx_roads_geometry ON roads USING GIST (geometry);
```

This creates a special index optimized for:
- Distance queries ("find all within X meters")
- Containment queries ("is this point inside this polygon?")
- Intersection queries ("which roads cross this zone?")

### Performance Impact

- Without index: 10+ seconds for complex queries
- With index: Milliseconds

Always create GIST indexes on geometry columns!

---

## Database Schema Summary

### Roads Table

| Column | Type | Description |
|--------|------|-------------|
| id | BigInteger | OpenStreetMap ID (primary key) |
| geometry | LINESTRING | Road path (PostGIS) |
| road_type | String | motorway, primary, etc. |
| surface | String | asphalt, gravel, etc. |
| smoothness | String | excellent, good, bad, etc. |
| name | String | Road name (nullable) |
| lanes | Integer | Number of lanes |
| oneway | Boolean | One-way restriction |
| max_speed | Integer | Speed limit in km/h (nullable) |
| tags | JSONB | Raw OSM tags |
| created_at | DateTime | When first inserted |
| updated_at | DateTime | When last updated |

**Indexes:**
- Primary key on `id`
- GIST index on `geometry`

### POIs Table

Similar structure with:
- `geometry` as POINT instead of LINESTRING
- `category` and `subcategory` instead of road-specific fields
- `address` as JSONB
- `phone`, `opening_hours`, `website`, `price_range` fields
- Search fields: `name_normalized`, `search_text`, `search_text_normalized`, `has_name`, `popularity`

### Zones Table

Similar structure with:
- `geometry` as MULTIPOLYGON instead of LINESTRING
- `zone_type` (country, region, district, commune, fokontany)
- `level`, `parent_zone_id`, `iso_code`, `population`

### Segments Table

Routing segments derived from roads (split at intersections):
- `road_id` references `roads.id`
- `geometry` as LINESTRING with start/end points
- `length`, `surface_factor`, `smoothness_factor`, `rainy_season_factor`
- `base_speed`, `effective_speed_kmh`, `travel_time_seconds`, `cost`
- `oneway` flag

---

## Example Queries

### Find All Primary Roads

```sql
SELECT id, name, road_type
FROM roads
WHERE road_type = 'primary';
```

### Find Gas Stations Near a Point

```sql
SELECT name, category, subcategory,
       ST_Distance(
           geometry,
           ST_GeomFromText('POINT(47.5079 -18.8792)', 4326)
       ) as distance_meters
FROM pois
WHERE subcategory = 'fuel'
  AND ST_DWithin(
      geometry,
      ST_GeomFromText('POINT(47.5079 -18.8792)', 4326),
      50000  -- 50 km in meters
  )
ORDER BY distance_meters;
```

### Find Which Region Contains a Point

```sql
SELECT name, zone_type
FROM zones
WHERE zone_type = 'region'
  AND ST_Contains(
      geometry,
      ST_GeomFromText('POINT(47.5079 -18.8792)', 4326)
  );
```

---

## Summary

The PostgreSQL Component:

**Purpose:**
- Store geographic data persistently
- Enable efficient spatial queries
- Implement the GeoRepository port

**Components:**
- **Connection Pool** - Manage database connections efficiently
- **PostgresWriter** - Save Domain entities to database
- **Migrations** - Manage schema changes over time

**Key Technologies:**
- **PostgreSQL** - Reliable, powerful database
- **PostGIS** - Geographic extensions
- **psycopg** - Async Python driver
- **Alembic** - Migration management

**Key Features:**
- Batch inserts (fast)
- Upserts (handle duplicates)
- Spatial indexes (fast queries)
- JSONB storage (flexible data)
- Async operations (non-blocking)

**Benefits:**
- Fast spatial queries
- Data persistence
- Version-controlled schema
- Industry-standard tools
