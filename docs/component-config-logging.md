# Configuration and Logging Components

## Configuration Component

### What is Configuration?

Configuration is all the settings that control how the application runs:
- Where is the OSM data file?
- How do we connect to the database?
- How many items should we process at once?
- What level of logging do we want?

These settings can change between:
- Development (your laptop)
- Testing (test environment)
- Production (real server)

### Why Separate Configuration?

Instead of hardcoding values:
```python
# ❌ Bad - hardcoded
db_host = "localhost"
db_port = 5432
```

We use configuration:
```python
# ✅ Good - configurable
db_host = settings.POSTGRES_HOST
db_port = settings.POSTGRES_PORT
```

Benefits:
- Easy to change without modifying code
- Different settings for dev/test/production
- Secrets (passwords) stay out of code
- Type-safe (catches mistakes early)

---

## How Configuration Works

### 1. Environment Variables

Settings come from environment variables or `.env` files:

**.env file:**
```bash
# OSM Data
OSM_FILE_PATH=data/madagascar-latest.osm.pbf

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lemurion
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret123

# Processing
BATCH_SIZE=1000

# Parallel Processing
ENABLE_PARALLEL_PIPELINE=true
PARALLEL_QUEUE_DEPTH=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=console
```

### 2. Settings Class

Pydantic validates and provides type-safe access:

```python
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application configuration settings.
    
    Values are loaded from:
    1. Environment variables
    2. .env file (if present)
    3. Default values (if specified)
    """
    
    # ==================
    # OSM Data Settings
    # ==================
    
    OSM_FILE_PATH: Path
    """
    Path to the OpenStreetMap .pbf file.
    
    Example: data/madagascar-latest.osm.pbf
    Required: Yes
    """
    
    # ==================
    # Database Settings
    # ==================
    
    POSTGRES_HOST: str = "localhost"
    """
    PostgreSQL server hostname or IP address.
    
    Default: localhost
    """
    
    POSTGRES_PORT: int = 5432
    """
    PostgreSQL server port.
    
    Default: 5432 (standard PostgreSQL port)
    """
    
    POSTGRES_DB: str = "lemurion"
    """
    Database name.
    
    Default: lemurion
    """
    
    POSTGRES_USER: str
    """
    Database username.
    
    Required: Yes
    """
    
    POSTGRES_PASSWORD: str
    """
    Database password.
    
    Required: Yes
    Security: Keep this secret! Don't commit to version control.
    """
    
    # ==================
    # Processing Settings
    # ==================
    
    BATCH_SIZE: int = 1000
    """
    Number of items to process in each batch.

    Larger batches:
    - Faster processing
    - More memory usage

    Smaller batches:
    - Slower processing
    - Less memory usage

    Default: 1000 (good balance)
    """

    # ==========================
    # Parallel Processing Settings
    # ==========================

    ENABLE_PARALLEL_PIPELINE: bool = True
    """
    Enable parallel processing mode.

    When True (default):
    - Uses producer-consumer pattern for overlapping extraction/loading
    - Processes independent entity types concurrently with asyncio.gather()
    - Typically 25-50% faster than sequential mode

    When False:
    - Processes entity types one at a time
    - Simpler execution flow, easier to debug
    - Use for troubleshooting or resource-constrained environments

    Default: True
    """

    PARALLEL_QUEUE_DEPTH: int = 10
    """
    Maximum number of batches to buffer in the async queue.

    This controls backpressure between extraction (producer) and
    database loading (consumer):

    Higher values:
    - More memory usage (more batches buffered)
    - Better throughput if extraction is faster than loading
    - Risk of memory exhaustion with very large batches

    Lower values:
    - Less memory usage
    - May cause extraction to wait for loading
    - Safer for memory-constrained environments

    Default: 10 (buffers up to 10 * BATCH_SIZE items)
    """

    # ==================
    # Logging Settings
    # ==================
    
    LOG_LEVEL: str = "INFO"
    """
    Logging level.
    
    Options:
    - DEBUG: Very detailed, for debugging
    - INFO: General information
    - WARNING: Warning messages
    - ERROR: Error messages only
    
    Default: INFO
    """
    
    LOG_FORMAT: str = "console"
    """
    Log output format.
    
    Options:
    - console: Human-readable, colored (for development)
    - json: Machine-readable JSON (for production)
    
    Default: console
    """
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
```

### 3. Using Settings

```python
from infrastructure.config import settings

# Type-safe access
print(settings.POSTGRES_HOST)  # IDE knows this is a string
print(settings.POSTGRES_PORT)  # IDE knows this is an int
print(settings.BATCH_SIZE)     # IDE knows this is an int

# Validation happens automatically
# If POSTGRES_PORT="abc", Pydantic raises an error at startup
```

---

## Configuration Benefits

### 1. Type Safety

```python
# ✅ Pydantic validates types
settings.POSTGRES_PORT  # Guaranteed to be an int

# If .env has POSTGRES_PORT=abc, you get an error immediately:
# "value is not a valid integer"
```

### 2. Default Values

```python
# Optional settings with defaults
POSTGRES_HOST: str = "localhost"  # Uses "localhost" if not specified

# Required settings without defaults
POSTGRES_USER: str  # Must be provided or error
```

### 3. Auto-Documentation

```python
# The type hints and docstrings document what each setting does
OSM_FILE_PATH: Path
"""
Path to the OpenStreetMap .pbf file.
Example: data/madagascar-latest.osm.pbf
Required: Yes
"""
```

### 4. Environment Flexibility

```bash
# Development
export POSTGRES_HOST=localhost
export LOG_LEVEL=DEBUG
python main.py

# Production
export POSTGRES_HOST=prod-db.example.com
export LOG_LEVEL=WARNING
python main.py
```

---

## Example Configuration Scenarios

### Development (Local)

**.env:**
```bash
OSM_FILE_PATH=data/madagascar-latest.osm.pbf
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lemurion_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password
BATCH_SIZE=100  # Smaller for testing
ENABLE_PARALLEL_PIPELINE=false  # Sequential for easier debugging
PARALLEL_QUEUE_DEPTH=5
LOG_LEVEL=DEBUG
LOG_FORMAT=console
```

### Testing

**.env.test:**
```bash
OSM_FILE_PATH=data/test-sample.osm.pbf
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lemurion_test
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password
BATCH_SIZE=10  # Very small for unit tests
ENABLE_PARALLEL_PIPELINE=false  # Sequential for deterministic tests
PARALLEL_QUEUE_DEPTH=2
LOG_LEVEL=DEBUG
LOG_FORMAT=console
```

### Production

**Environment variables (no .env file for security):**
```bash
export OSM_FILE_PATH=/data/madagascar-latest.osm.pbf
export POSTGRES_HOST=10.0.1.50
export POSTGRES_PORT=5432
export POSTGRES_DB=lemurion
export POSTGRES_USER=app_user
export POSTGRES_PASSWORD=<secret-from-vault>
export BATCH_SIZE=5000  # Larger for performance
export ENABLE_PARALLEL_PIPELINE=true  # Parallel for maximum throughput
export PARALLEL_QUEUE_DEPTH=20  # More buffering for high throughput
export LOG_LEVEL=INFO
export LOG_FORMAT=json  # For log analysis tools
```

---

## Logging Component

### What is Logging?

Logging is recording what the application does:
- "Started importing roads"
- "Saved batch of 1000 POIs"
- "Database connection failed"
- "Import complete: 50,000 roads processed"

Logs help:
- Understand what the application is doing
- Debug problems
- Monitor performance
- Audit operations

### Why Structured Logging?

**Traditional logging (strings):**
```python
logger.info("Imported 1500 roads in 2.5 seconds")
```

Hard to search and analyze. How do you find all imports that took > 2 seconds?

**Structured logging (dictionaries):**
```python
logger.info("roads_imported", count=1500, duration=2.5)
```

Easy to search: "show me all logs where duration > 2"

---

## Setting Up Logging

### Configuration with structlog

```python
import logging
import structlog
from infrastructure.config import settings

def setup_logging():
    """
    Configure structured logging with structlog.
    
    Formats:
    - console: Human-readable with colors
    - json: Machine-readable for production
    """
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Choose processors based on format
    if settings.LOG_FORMAT == "json":
        # JSON format for production
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console format for development
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),  # Colored, readable
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

---

## Using Logging

### Basic Logging

```python
import structlog

logger = structlog.get_logger()

# Simple message
logger.info("application_started")

# With context
logger.info("importing_roads", file_path="madagascar.pbf")

# Different levels
logger.debug("detailed_info", item_id=12345)
logger.info("general_info", status="processing")
logger.warning("potential_problem", retry_count=3)
logger.error("error_occurred", error_type="DatabaseError")
```

### Output Examples

**Console format (development):**
```
2026-01-15 10:30:45 [info     ] application_started
2026-01-15 10:30:46 [info     ] importing_roads        file_path=madagascar.pbf
2026-01-15 10:30:47 [info     ] roads_imported         count=1500 duration=2.5
2026-01-15 10:30:48 [warning  ] slow_operation         operation=save duration=5.2
2026-01-15 10:30:49 [error    ] database_error         error=ConnectionError
```

**JSON format (production):**
```json
{"event": "application_started", "level": "info", "timestamp": "2026-01-15T10:30:45.123Z"}
{"event": "importing_roads", "file_path": "madagascar.pbf", "level": "info", "timestamp": "2026-01-15T10:30:46.234Z"}
{"event": "roads_imported", "count": 1500, "duration": 2.5, "level": "info", "timestamp": "2026-01-15T10:30:47.345Z"}
```

---

## Logging Best Practices

### 1. Use Structured Data

```python
# ❌ String message (hard to search)
logger.info(f"Imported {count} roads in {duration} seconds")

# ✅ Structured (easy to search and analyze)
logger.info("roads_imported", count=count, duration=duration)
```

### 2. Use Consistent Event Names

```python
# Good naming convention: object_action
logger.info("roads_imported", ...)
logger.info("pois_saved", ...)
logger.info("database_connected", ...)
logger.error("file_read_failed", ...)
```

### 3. Add Useful Context

```python
# ❌ Too little context
logger.error("save_failed")

# ✅ Helpful context
logger.error(
    "batch_save_failed",
    entity_type="road",
    batch_size=1000,
    attempt=3,
    error_message=str(e)
)
```

### 4. Use Appropriate Levels

```python
# DEBUG: Very detailed, temporary
logger.debug("processing_item", item_id=123, step="validation")

# INFO: Normal operations
logger.info("batch_completed", count=1000, total=50000)

# WARNING: Potential problems
logger.warning("slow_query", duration=5.2, query="SELECT ...")

# ERROR: Actual errors
logger.error("import_failed", file="data.pbf", error=str(e))
```

### 5. Log at Key Points

```python
async def import_roads():
    logger.info("import_started", entity="roads")
    
    total = 0
    try:
        for batch in batches:
            await save_batch(batch)
            total += len(batch)
            logger.debug("batch_saved", count=len(batch), total=total)
        
        logger.info("import_completed", entity="roads", total=total)
    except Exception as e:
        logger.error("import_failed", entity="roads", error=str(e))
        raise
```

---

## Log Levels Explained

### DEBUG
Very detailed information for diagnosing problems.

**When to use:**
- Temporary debugging
- Detailed flow tracking
- Variable values

**Example:**
```python
logger.debug("validating_road", id=12345, tags=tags)
```

### INFO
Confirmation that things are working as expected.

**When to use:**
- Major steps completed
- Application lifecycle events
- Statistics and summaries

**Example:**
```python
logger.info("batch_imported", entity="roads", count=1000, elapsed=2.5)
```

### WARNING
Something unexpected happened, but the application can continue.

**When to use:**
- Slow operations
- Retries
- Deprecated features
- Missing optional data

**Example:**
```python
logger.warning("missing_optional_data", id=12345, field="name")
```

### ERROR
A serious problem prevented an operation from completing.

**When to use:**
- Exceptions
- Failed operations
- Data corruption

**Example:**
```python
logger.error("database_save_failed", entity="roads", error=str(e))
```

---

## Complete Example

```python
from infrastructure.config import settings
from infrastructure.logging import setup_logging
import structlog

# Setup logging at application startup
setup_logging()
logger = structlog.get_logger()

async def main():
    logger.info(
        "application_started",
        osm_file=str(settings.OSM_FILE_PATH),
        batch_size=settings.BATCH_SIZE
    )
    
    try:
        # Connect to database
        logger.info("connecting_to_database", host=settings.POSTGRES_HOST)
        pool = await create_pool(settings)
        logger.info("database_connected")
        
        # Create components
        reader = PBFReader(settings.OSM_FILE_PATH)
        extractor = OSMExtractor(reader)
        repository = PostgresWriter(pool, settings.BATCH_SIZE)
        
        # Run pipeline
        pipeline = RunPipelineUseCase(extractor, repository, settings.BATCH_SIZE)
        
        logger.info("pipeline_started")
        await pipeline.execute()
        logger.info("pipeline_completed")
        
    except Exception as e:
        logger.error("application_failed", error=str(e), error_type=type(e).__name__)
        raise
    finally:
        logger.info("application_shutdown")
```

**Output (console format):**
```
2026-01-15 10:30:00 [info] application_started      osm_file=data/madagascar.pbf batch_size=1000
2026-01-15 10:30:01 [info] connecting_to_database   host=localhost
2026-01-15 10:30:02 [info] database_connected
2026-01-15 10:30:02 [info] pipeline_started
2026-01-15 10:35:45 [info] pipeline_completed
2026-01-15 10:35:45 [info] application_shutdown
```

---

## Summary

### Configuration Component

**Purpose:**
- Manage application settings
- Separate configuration from code
- Validate settings at startup

**Features:**
- Environment variables and .env files
- Type-safe with Pydantic
- Default values
- Required vs optional settings
- Auto-documentation

**Benefits:**
- No hardcoded values
- Different settings per environment
- Catches configuration errors early
- Secrets stay out of code

---

### Logging Component

**Purpose:**
- Record application activities
- Help debugging and monitoring
- Provide audit trail

**Features:**
- Structured logging (dictionaries, not strings)
- Multiple formats (console for dev, JSON for production)
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Automatic context (timestamps, log levels, etc.)

**Benefits:**
- Easy to search and analyze
- Readable in development
- Machine-readable in production
- Integrates with log analysis tools
- Provides operational visibility

---

## Best Practices Summary

### Configuration
✅ Use environment variables for all settings  
✅ Provide sensible defaults where appropriate  
✅ Keep secrets in environment, never in code  
✅ Document each setting with docstrings  
✅ Use Pydantic for validation  

### Logging
✅ Use structured logging  
✅ Choose appropriate log levels  
✅ Add useful context to logs  
✅ Use consistent event naming  
✅ Log at key application points  
✅ Use JSON format in production  
✅ Use console format in development  
