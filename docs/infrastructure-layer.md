# Infrastructure Layer

## What is the Infrastructure Layer?

The Infrastructure Layer handles all the "dirty work" of dealing with the outside world:
- Reading files from disk
- Connecting to databases
- Making network requests
- Reading configuration files
- Writing log messages

Think of it as the **hands and feet** of the application - it does the actual physical work, while the Domain (brain) and Application (coordinator) tell it what to do.

## Why Separate Infrastructure?

Keeping infrastructure separate makes the application:
1. **Testable** - You can test business logic without real databases
2. **Flexible** - You can swap PostgreSQL for MongoDB without changing business logic
3. **Portable** - You can run the same code on different systems
4. **Maintainable** - External dependencies are isolated in one place

## What's Inside?

The Infrastructure Layer has four main components:

```
infrastructure/
├── osm/              # OpenStreetMap data extraction
├── postgres/         # PostgreSQL database access
├── config/           # Configuration management
└── logging/          # Structured logging
```

---

## Component Overview

### 1. OSM Component

**Purpose:** Extract geographic data from OpenStreetMap `.pbf` files and convert it into Domain entities.

**Files:**
- `reader.py` - Reads raw bytes from .pbf files using osmium
- `extractor.py` - Implements the DataExtractor port, converts OSM data to Domain entities
- `transformers.py` - Converts OSM tags to Domain enums and value objects
- `handlers.py` - Osmium handlers that collect nodes, ways, and relations
- `types.py` - Data structures for raw OSM data (before conversion to Domain)

**What it does:**
1. Opens a `.pbf` file (compressed OpenStreetMap data)
2. Reads through all nodes, ways, and relations
3. Filters for relevant data (roads, POIs, zones)
4. Converts OSM-specific data to clean Domain entities
5. Yields them one at a time (memory efficient)

**Example:**
```
.pbf file → PBFReader → OSMExtractor → Road/POI/Zone entities
```

---

### 2. Postgres Component

**Purpose:** Save geographic data to a PostgreSQL database with PostGIS extension.

**Files:**
- `connection.py` - Manages database connection pools
- `writer.py` - Implements the GeoRepository port, saves entities to database
- `migrations/` - Alembic database migrations (schema changes)

**What it does:**
1. Creates async connection pool to PostgreSQL
2. Converts Domain entities to SQL INSERT/UPDATE statements
3. Batches multiple operations for speed
4. Uses PostGIS to store geometries (points, lines, polygons)
5. Handles conflicts (updates existing records)

**Example:**
```
Road entities → PostgresWriter → SQL statements → PostgreSQL database
```

---

### 3. Config Component

**Purpose:** Load and validate configuration from environment variables and `.env` files.

**Files:**
- `settings.py` - Defines all configuration settings using Pydantic

**What it does:**
1. Reads environment variables
2. Reads `.env` file if it exists
3. Validates values (e.g., port must be a number)
4. Provides type-safe access to configuration
5. Sets sensible defaults

**Example:**
```
.env file → Pydantic Settings → Validated configuration object
```

---

### 4. Logging Component

**Purpose:** Provide structured, consistent logging throughout the application.

**Files:**
- `setup.py` - Configures structlog for JSON or console logging

**What it does:**
1. Sets up structured logging (logs are dictionaries, not just strings)
2. Adds context automatically (timestamps, log levels, etc.)
3. Can output human-readable console logs or machine-readable JSON
4. Integrates with standard Python logging

**Example:**
```
log.info("importing_roads", count=1500) → Structured log entry
```

---

## How Infrastructure Implements Ports

The Infrastructure Layer provides concrete implementations of the ports defined in the Application Layer.

### DataExtractor Port Implementation

**Port (Application Layer):**
```python
class DataExtractor(ABC):
    @abstractmethod
    def extract_roads(self) -> Iterator[Road]:
        pass
```

**Implementation (Infrastructure Layer):**
```python
class OSMExtractor(DataExtractor):
    def __init__(self, pbf_reader: PBFReader):
        self.reader = pbf_reader
    
    def extract_roads(self) -> Iterator[Road]:
        for raw_way in self.reader.ways():
            if self._is_road(raw_way):
                road = self._convert_to_road(raw_way)
                yield road
```

### GeoRepository Port Implementation

**Port (Application Layer):**
```python
class GeoRepository(ABC):
    @abstractmethod
    async def save_roads(self, roads: List[Road]) -> None:
        pass
```

**Implementation (Infrastructure Layer):**
```python
class PostgresWriter(GeoRepository):
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool
    
    async def save_roads(self, roads: List[Road]) -> None:
        async with self.pool.connection() as conn:
            for road in roads:
                await conn.execute(
                    "INSERT INTO roads (...) VALUES (...)",
                    [road.id, road.name, ...]
                )
```

---

## The Dependency Flow

```
┌─────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE                      │
│                                                     │
│  Depends on:                                        │
│  - Application (implements its ports)               │
│  - Domain (creates/uses its entities)               │
│  - External libraries (osmium, psycopg, pydantic)   │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────┐  │
│  │   OSM    │  │ Postgres │  │ Config │  │ Logs │  │
│  └────┬─────┘  └─────┬────┘  └───┬────┘  └───┬──┘  │
│       │              │            │           │     │
└───────┼──────────────┼────────────┼───────────┼─────┘
        │              │            │           │
        │ creates      │ saves      │ provides  │ writes
        ▼              ▼            ▼           ▼
┌──────────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐
│ Domain       │ │ Domain   │ │Settings │ │Log      │
│ Entities     │ │ Entities │ │         │ │Messages │
└──────────────┘ └──────────┘ └─────────┘ └─────────┘
```

---

## Key Characteristics

### 1. Implements, Doesn't Define

Infrastructure implements interfaces (ports) defined by Application:
- ✅ OSMExtractor implements DataExtractor
- ✅ PostgresWriter implements GeoRepository
- ❌ Infrastructure doesn't define what a Road is (that's Domain)
- ❌ Infrastructure doesn't define the use cases (that's Application)

### 2. Technology-Specific

This layer knows about specific technologies:
- `osmium` library for reading .pbf files
- `psycopg` for PostgreSQL
- `pydantic` for configuration
- `structlog` for logging

The Domain and Application layers know nothing about these.

### 3. Replaceable

Because infrastructure implements well-defined ports, you can replace implementations:

**Currently:**
```python
extractor = OSMExtractor(pbf_reader)  # Reads from .pbf files
repository = PostgresWriter(pool)     # Saves to PostgreSQL
```

**Future alternatives:**
```python
extractor = GeoJSONExtractor(file)    # Read from GeoJSON instead
repository = MongoWriter(client)      # Save to MongoDB instead
```

The use cases wouldn't need to change!

### 4. Side Effects

Infrastructure is where side effects happen:
- Reading files
- Writing to databases
- Network requests
- Printing to console
- Modifying global state

The Domain layer has NO side effects (pure functions).

---

## Common Patterns

### Pattern 1: Adapter Pattern

Infrastructure adapters convert between external formats and domain models:

```
OSM tags          →  OSMTransformers  →  Domain entities
(external format)     (adapter)          (internal format)
```

Example:
```python
# OSM tag: highway=primary
osm_highway = "primary"

# Adapter converts to domain enum
road_type = RoadTypeTransformer.from_osm(osm_highway)
# Result: RoadType.PRIMARY
```

### Pattern 2: Factory Pattern

Infrastructure often uses factories to create complex objects:

```python
async def create_pool(settings: Settings) -> AsyncConnectionPool:
    """
    Factory function to create a database connection pool.
    """
    return AsyncConnectionPool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )
```

### Pattern 3: Repository Pattern

PostgresWriter is a repository - it hides the complexity of data storage:

```python
# Simple interface
await repository.save_roads(roads)

# Behind the scenes:
# - Convert entities to SQL
# - Batch operations
# - Handle transactions
# - Manage connections
# - Handle errors
```

---

## Error Handling

Infrastructure is where things can go wrong:
- File not found
- Database connection failed
- Invalid data format
- Network timeout

Infrastructure translates these into domain exceptions:

```python
try:
    road = self._parse_osm_way(raw_way)
except KeyError:
    # OSM data is missing required field
    raise DataExtractionError(f"Invalid OSM way: {raw_way.id}")

try:
    await conn.execute(sql)
except psycopg.DatabaseError as e:
    # Database problem
    raise DataStorageError(f"Failed to save roads: {e}")
```

---

## Configuration Management

All external configuration is centralized in `config/settings.py`:

```python
class Settings(BaseSettings):
    # OSM file location
    OSM_FILE_PATH: Path
    
    # Database connection
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "lemurion"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    
    # Processing
    BATCH_SIZE: int = 1000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "console"  # or "json"
    
    class Config:
        env_file = ".env"
```

**Benefits:**
- Type-safe (IDE knows POSTGRES_PORT is an int)
- Validated automatically
- Single source of truth
- Easy to change without modifying code

---

## Logging Best Practices

Use structured logging with context:

```python
# ❌ String logging (hard to search/filter)
logger.info("Imported 1500 roads")

# ✅ Structured logging (easy to search/filter)
logger.info("imported_roads", count=1500, batch=1)

# ✅ With context
logger.info(
    "saving_batch",
    entity_type="road",
    batch_size=1000,
    total_processed=5000
)
```

Benefits:
- Easy to search logs: "show me all logs where count > 1000"
- Can be sent to log analysis tools (Elasticsearch, etc.)
- Includes automatic context (timestamp, log level, module name)

---

## Database Migrations

Schema changes are managed with Alembic:

```bash
# Create a new migration
cd src/infrastructure/postgres/migrations
alembic revision -m "add_segments_table"

# Edit the generated file to add:
def upgrade():
    op.create_table(
        'segments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('road_id', sa.Integer),
        ...
    )

def downgrade():
    op.drop_table('segments')

# Apply the migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

**Benefits:**
- Version control for database schema
- Can rollback changes
- Can see history of changes
- Can apply migrations in production safely

---

## Performance Considerations

### 1. Batching

Don't save one item at a time:
```python
# ❌ Slow - many small database operations
for road in roads:
    await repository.save_road(road)

# ✅ Fast - one large batch operation
await repository.save_roads(roads)  # Save 1000 at once
```

### 2. Connection Pooling

Reuse database connections:
```python
# ❌ Slow - create new connection each time
async def save(road):
    conn = await create_connection()
    await conn.execute(...)
    await conn.close()

# ✅ Fast - reuse connections from pool
pool = await create_pool()
async with pool.connection() as conn:
    await conn.execute(...)
```

### 3. Async/Await

Use async for I/O operations:
```python
# ✅ Database operations are async
async def save_roads(self, roads):
    await conn.execute(...)

# ✅ Can process data while waiting for DB
async def pipeline():
    await asyncio.gather(
        repository.save_roads(roads),
        repository.save_pois(pois)
    )
```

### 4. Streaming

Process large files in chunks:
```python
# ❌ Load entire file into memory
roads = list(extractor.extract_roads())  # Could be millions!
await repository.save_roads(roads)

# ✅ Process in batches
batch = []
for road in extractor.extract_roads():  # Generator - one at a time
    batch.append(road)
    if len(batch) >= 1000:
        await repository.save_roads(batch)
        batch = []
```

---

## Testing Infrastructure

Infrastructure testing usually requires external systems:

### Unit Tests (with mocks)
```python
@pytest.mark.asyncio
async def test_save_roads():
    # Mock the database connection
    mock_pool = Mock()
    writer = PostgresWriter(mock_pool)
    
    roads = [Road(...), Road(...)]
    await writer.save_roads(roads)
    
    # Verify SQL was called
    mock_pool.execute.assert_called()
```

### Integration Tests (with real systems)
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_retrieve_roads():
    # Use a test database
    pool = await create_pool(test_settings)
    writer = PostgresWriter(pool)
    
    # Save real data
    roads = [create_test_road()]
    await writer.save_roads(roads)
    
    # Verify it was saved
    result = await pool.execute("SELECT * FROM roads")
    assert len(result) == 1
```

---

## Summary

The Infrastructure Layer:

**Purpose:**
- Interact with external systems (files, databases, networks)
- Implement ports defined by Application Layer
- Convert between external formats and Domain models

**Components:**
- **OSM** - Extract data from OpenStreetMap files
- **Postgres** - Save data to PostgreSQL database
- **Config** - Manage configuration settings
- **Logging** - Provide structured logging

**Characteristics:**
- Technology-specific (knows about osmium, psycopg, etc.)
- Replaceable (can swap implementations)
- Where side effects happen
- Where errors are handled

**Best Practices:**
- Batch operations for performance
- Use connection pooling
- Use async for I/O
- Stream large datasets
- Use structured logging
- Manage schema with migrations
