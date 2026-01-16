# Application Layer

## What is the Application Layer?

The Application Layer sits between the Domain (business logic) and Infrastructure (external systems). It orchestrates how the application does its work by coordinating the domain objects and infrastructure components.

Think of it as a **coordinator** or **conductor of an orchestra** - it tells different parts when to play, but doesn't do the actual playing.

## Why Do We Need It?

Imagine you want to import road data from OpenStreetMap and save it to PostgreSQL. This requires:
1. Reading the OSM file (Infrastructure)
2. Creating Road objects (Domain)
3. Saving to the database (Infrastructure)

The Application Layer coordinates these steps in the right order.

## Three Main Components

### 1. Ports (Interfaces)

Ports are like contracts that define what the Infrastructure must do, without saying how to do it.

Think of a port as a job description:
- "We need someone who can extract road data"
- "We need someone who can save data to a database"

The Infrastructure Layer provides the actual implementations (the "employees who do the job").

### 2. Services

Services are reusable utilities that support use cases. They handle cross-cutting concerns like:
- Async batch processing (producer-consumer patterns)
- Rate limiting
- Caching strategies

### 3. Use Cases

Use Cases are the actual tasks the application performs. Each use case represents one complete action a user might want.

Examples:
- "Import OSM data and save to database"
- "Find all hotels within 50 km of a road"
- "Calculate the fastest route between two points"

---

## Ports Explained

### What are Ports?

Ports are Python **abstract classes** or **protocols** that define methods without implementing them. They specify:
- What methods must exist
- What parameters they take
- What they return

But they don't specify HOW to do it.

### Why Use Ports?

**Dependency Inversion Principle**: High-level code (Application) shouldn't depend on low-level details (Infrastructure). Both should depend on abstractions (Ports).

Benefits:
1. **Testability** - You can test use cases with fake implementations
2. **Flexibility** - You can swap PostgreSQL for MySQL without changing use cases
3. **Clarity** - The port clearly states what's needed

### The Two Main Ports

#### 1. DataExtractor Port

Defines how to extract data from a source (like OpenStreetMap files).

```python
from abc import ABC, abstractmethod
from domain.entities import Road, POI, Zone

class DataExtractor(ABC):
    """
    Port (interface) for extracting geographic data.
    
    Implementations might read from:
    - OSM .pbf files
    - GeoJSON files  
    - Web APIs
    """
    
    @abstractmethod
    def extract_roads(self) -> Iterator[Road]:
        """
        Get all roads from the data source.
        
        Returns:
            Iterator of Road entities
        """
        pass
    
    @abstractmethod
    def extract_pois(self) -> Iterator[POI]:
        """
        Get all points of interest from the data source.
        
        Returns:
            Iterator of POI entities
        """
        pass
    
    @abstractmethod
    def extract_zones(self) -> Iterator[Zone]:
        """
        Get all administrative zones from the data source.
        
        Returns:
            Iterator of Zone entities
        """
        pass
```

**Key Points:**
- Returns iterators (generators) for memory efficiency
- Returns Domain entities (Road, POI, Zone), not raw data
- Doesn't specify the data source (could be OSM, GeoJSON, etc.)

#### 2. GeoRepository Port

Defines how to save geographic data to persistent storage.

```python
from abc import ABC, abstractmethod
from typing import List
from domain.entities import Road, POI, Zone

class GeoRepository(ABC):
    """
    Port (interface) for storing geographic data.
    
    Implementations might save to:
    - PostgreSQL with PostGIS
    - SQLite with SpatiaLite
    - MongoDB
    """
    
    @abstractmethod
    async def save_roads(self, roads: List[Road]) -> None:
        """
        Save roads to storage.
        
        Args:
            roads: List of Road entities to save
        """
        pass
    
    @abstractmethod
    async def save_pois(self, pois: List[POI]) -> None:
        """
        Save points of interest to storage.
        
        Args:
            pois: List of POI entities to save
        """
        pass
    
    @abstractmethod
    async def save_zones(self, zones: List[Zone]) -> None:
        """
        Save zones to storage.
        
        Args:
            zones: List of Zone entities to save
        """
        pass
```

**Key Points:**
- Methods are async (for performance with databases)
- Takes Domain entities as input
- Doesn't specify storage mechanism (could be any database)

---

## Services Explained

### What are Services?

Services are reusable utilities that support use cases but don't represent business workflows themselves. They handle technical concerns that are needed by multiple use cases.

### The AsyncBatcher Service

The `AsyncBatcher` implements a **producer-consumer pattern** to overlap CPU-bound extraction with I/O-bound database loading.

#### The Problem It Solves

Without AsyncBatcher (sequential):
```
Extract batch 1 → Wait → Save batch 1 → Extract batch 2 → Wait → Save batch 2 → ...
                  ↑                                       ↑
            CPU idle                                 CPU idle
```

The CPU sits idle while waiting for database writes.

With AsyncBatcher (parallel):
```
Producer (extraction):  [Extract 1] [Extract 2] [Extract 3] [Extract 4] ...
                             │           │           │           │
                             ▼           ▼           ▼           ▼
Queue (buffer):           [batch1] → [batch2] → [batch3] → [batch4] → ...
                             │           │           │           │
                             ▼           ▼           ▼           ▼
Consumer (database):      [Save 1]   [Save 2]   [Save 3]   [Save 4] ...
```

Extraction and saving happen simultaneously!

#### How It Works

```python
from collections.abc import Awaitable, Callable, Iterator
from typing import Generic, TypeVar
import asyncio

T = TypeVar("T")

class AsyncBatcher(Generic[T]):
    """Converts sync iterator to async batches via queue.

    Producer-consumer pattern where:
    - Producer: Runs sync extraction in executor (doesn't block event loop)
    - Queue: Buffers batches between producer and consumer
    - Consumer: Processes batches asynchronously (database writes)
    """

    def __init__(
        self,
        iterator: Iterator[T],
        batch_size: int = 1000,
        max_queue_size: int = 10,
    ) -> None:
        """Initialize the batcher.

        Args:
            iterator: Sync iterator yielding items to batch
            batch_size: Number of items per batch
            max_queue_size: Max batches to buffer (backpressure control)
        """
        self.iterator = iterator
        self.batch_size = batch_size
        self.queue: asyncio.Queue[list[T] | None] = asyncio.Queue(max_queue_size)

    async def produce(self) -> None:
        """Producer: read from iterator in executor, enqueue batches."""
        loop = asyncio.get_event_loop()
        while True:
            # Run sync code in thread pool (doesn't block event loop)
            batch = await loop.run_in_executor(None, self._iter_batches)
            if batch is None:
                await self.queue.put(None)  # Signal end
                break
            await self.queue.put(batch)

    async def consume(
        self,
        processor: Callable[[list[T]], Awaitable[int]],
    ) -> int:
        """Consumer: process batches from queue asynchronously."""
        total = 0
        while True:
            batch = await self.queue.get()
            if batch is None:
                break
            total += await processor(batch)
        return total

    async def run(
        self,
        processor: Callable[[list[T]], Awaitable[int]],
    ) -> int:
        """Run producer and consumer concurrently."""
        producer = asyncio.create_task(self.produce())
        consumer = asyncio.create_task(self.consume(processor))
        await producer
        return await consumer
```

#### Key Design Decisions

1. **run_in_executor()**: Runs sync extraction code in a thread pool so it doesn't block the async event loop.

2. **Bounded Queue**: `max_queue_size` prevents memory exhaustion if extraction is faster than database writes.

3. **Sentinel Value**: `None` signals the consumer that production is complete.

4. **Generic Type**: Works with any entity type (Road, POI, Zone, Segment).

#### Usage Example

```python
from application.services import AsyncBatcher

# Create batcher for roads
batcher: AsyncBatcher[Road] = AsyncBatcher(
    extractor.extract_roads(),  # Sync iterator
    batch_size=1000,
    max_queue_size=10,
)

# Run with async processor
total = await batcher.run(repository.save_roads_batch)
print(f"Saved {total} roads")
```

---

## Use Cases Explained

### What are Use Cases?

Use Cases implement specific business workflows. Each use case:
1. Takes input (parameters)
2. Uses ports to interact with infrastructure
3. Coordinates domain logic
4. Returns output or performs actions

### The Main Use Case: RunPipeline

This is the primary use case that imports OpenStreetMap data into the database. It supports two execution modes: **sequential** (fallback) and **parallel** (default).

#### What It Does

**Sequential Mode:**
```
1. Extract roads from OSM file
2. Batch them (group into sets of 1000)
3. Save each batch to database
4. Repeat for POIs
5. Repeat for Zones
6. Generate segments from roads
7. Save segments
8. Log progress throughout
```

**Parallel Mode:**
```
1. Phase 1: Process roads (segments depend on roads)
   - Extract roads with producer-consumer pattern
   - Save roads while extracting more
2. Phase 2: Process segments, POIs, zones concurrently
   - asyncio.gather() runs all three in parallel
   - Each uses its own producer-consumer queue
3. Log progress throughout
```

#### The Code Structure

```python
from application.ports import DataExtractor, GeoRepository
from application.services import AsyncBatcher

class RunPipelineUseCase:
    """
    Use case for running the complete data import pipeline.

    Supports two execution modes:
    - Sequential: Processes entities one type at a time
    - Parallel: Uses producer-consumer pattern and asyncio.gather
    """

    def __init__(
        self,
        extractor: DataExtractor,
        repository: GeoRepository,
        enable_parallel: bool = True,
        batch_size: int = 1000,
        queue_depth: int = 10,
    ):
        """
        Initialize the use case.

        Args:
            extractor: Data source (implements DataExtractor port)
            repository: Data storage (implements GeoRepository port)
            enable_parallel: Enable parallel processing (default True)
            batch_size: How many items per batch
            queue_depth: Max batches to buffer in queue
        """
        self.extractor = extractor
        self.repository = repository
        self.enable_parallel = enable_parallel
        self.batch_size = batch_size
        self.queue_depth = queue_depth

    async def execute(
        self,
        entity_types: set[str] | None = None,
    ) -> PipelineResult:
        """
        Run the pipeline for specified entity types.

        Args:
            entity_types: Set of types to process.
                         None means all: {"roads", "pois", "zones", "segments"}

        Returns:
            PipelineResult with counts and duration.
        """
        types = entity_types or {"roads", "pois", "zones", "segments"}

        if self.enable_parallel:
            try:
                return await self._execute_parallel(types)
            except Exception:
                # Fallback to sequential on failure
                return await self._execute_sequential(types)

        return await self._execute_sequential(types)

    async def _process_with_queue(
        self,
        iterator: Iterator[T],
        save_batch_fn: Callable[[list[T]], Awaitable[int]],
    ) -> int:
        """Process entities using producer-consumer pattern."""
        batcher = AsyncBatcher(
            iterator,
            batch_size=self.batch_size,
            max_queue_size=self.queue_depth,
        )
        return await batcher.run(save_batch_fn)

    async def _execute_parallel(self, types: set[str]) -> PipelineResult:
        """Parallel execution with concurrent entity processing."""
        # Phase 1: Roads first (segments depend on them)
        roads = []
        if "roads" in types or "segments" in types:
            roads = list(self.extractor.extract_roads())
            if "roads" in types:
                await self._process_with_queue(
                    iter(roads),
                    self.repository.save_roads_batch,
                )

        # Phase 2: Segments, POIs, Zones run concurrently
        tasks = []
        if "segments" in types and roads:
            segments = split_roads_into_segments(roads)
            tasks.append(self._process_with_queue(
                iter(segments),
                self.repository.save_segments_batch,
            ))
        if "pois" in types:
            tasks.append(self._process_with_queue(
                self.extractor.extract_pois(),
                self.repository.save_pois_batch,
            ))
        if "zones" in types:
            tasks.append(self._process_with_queue(
                self.extractor.extract_zones(),
                self.repository.save_zones_batch,
            ))

        # Run all tasks concurrently
        await asyncio.gather(*tasks)
        return PipelineResult(...)
```

#### How It Works

**Dependency Injection:**
The use case receives its dependencies (extractor, repository) from outside. This means:
- It doesn't know if data comes from OSM or GeoJSON
- It doesn't know if data goes to PostgreSQL or SQLite
- It just knows the interfaces (ports)

**Producer-Consumer Pattern:**
Instead of extract → wait → save → extract → wait → save:
```
Producer (extract):  [batch1] [batch2] [batch3] ...
                        │        │        │
                        ▼        ▼        ▼
Queue (buffer):      [────────────────────────]
                        │        │        │
                        ▼        ▼        ▼
Consumer (save):     [batch1] [batch2] [batch3] ...
```

Extraction and saving happen simultaneously!

**Concurrent Entity Processing:**
In parallel mode, independent entity types process concurrently:
```python
await asyncio.gather(
    process_segments(),  # ─┐
    process_pois(),      # ─┼─ All run at the same time
    process_zones(),     # ─┘
)
```

**Graceful Fallback:**
If parallel mode fails, the use case automatically falls back to sequential mode:
```python
if self.enable_parallel:
    try:
        return await self._execute_parallel(types)
    except Exception:
        return await self._execute_sequential(types)  # Fallback
```

**Async/Await:**
The use case uses async methods because database operations can be slow. This allows other work to happen while waiting for the database.

---

## How the Application Layer Connects Everything

```
┌─────────────────────────────────────────────┐
│           Infrastructure Layer              │
│  ┌──────────────┐      ┌─────────────────┐  │
│  │ OSMExtractor │      │ PostgresWriter  │  │
│  │ (implements  │      │ (implements     │  │
│  │ DataExtractor│      │ GeoRepository)  │  │
│  │ port)        │      │                 │  │
│  └──────┬───────┘      └────────▲────────┘  │
└─────────┼─────────────────────────┼─────────┘
          │                         │
          │ provides                │ provides
          │                         │
┌─────────▼─────────────────────────┼─────────┐
│          Application Layer        │         │
│  ┌──────────────────┐             │         │
│  │ DataExtractor    │             │         │
│  │ (port/interface) │             │         │
│  └──────────────────┘             │         │
│                                   │         │
│  ┌────────────────────────────────┴──────┐  │
│  │ GeoRepository                         │  │
│  │ (port/interface)                      │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ RunPipelineUseCase                    │  │
│  │                                       │  │
│  │ Uses both ports to:                   │  │
│  │ 1. Extract data                       │  │
│  │ 2. Process in batches                 │  │
│  │ 3. Save to repository                 │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Example: Running the Pipeline

Here's how all the pieces fit together:

```python
import asyncio
from infrastructure.osm import PBFReader, OSMExtractor
from infrastructure.postgres import create_pool, PostgresWriter
from infrastructure.config import settings
from application.use_cases import RunPipelineUseCase

async def main():
    # 1. Create infrastructure implementations

    # Data source (OSM file)
    pbf_reader = PBFReader(settings.osm_file_path)
    extractor = OSMExtractor(pbf_reader)  # Implements DataExtractor port

    # Data storage (PostgreSQL)
    async with create_pool(settings) as pool:
        repository = PostgresWriter(pool, settings.batch_size)

        # 2. Create the use case with dependencies
        pipeline = RunPipelineUseCase(
            extractor=extractor,
            repository=repository,
            enable_parallel=settings.enable_parallel_pipeline,  # Default: True
            batch_size=settings.batch_size,
            queue_depth=settings.parallel_queue_depth,
        )

        # 3. Run it!
        result = await pipeline.execute()

        print(f"Pipeline complete!")
        print(f"  Roads: {result.roads_count}")
        print(f"  POIs: {result.pois_count}")
        print(f"  Zones: {result.zones_count}")
        print(f"  Segments: {result.segments_count}")
        print(f"  Duration: {result.duration_seconds}s")

# Run the async main function
asyncio.run(main())
```

### Running Specific Entity Types

You can process only specific entity types:

```python
# Only roads and POIs (no zones or segments)
result = await pipeline.execute(entity_types={"roads", "pois"})

# Only zones
result = await pipeline.execute(entity_types={"zones"})
```

### Disabling Parallel Mode

For debugging or simpler environments:

```bash
# Via environment variable
ENABLE_PARALLEL_PIPELINE=false python -m main
```

Or programmatically:

```python
pipeline = RunPipelineUseCase(
    extractor=extractor,
    repository=repository,
    enable_parallel=False,  # Sequential mode
)
```

## Testing the Application Layer

Because the Application Layer uses ports, testing is easy:

```python
class FakeExtractor(DataExtractor):
    """Fake data source for testing."""
    
    def extract_roads(self):
        # Return fake test data
        yield Road(osm_id=1, road_type=RoadType.PRIMARY, ...)
        yield Road(osm_id=2, road_type=RoadType.SECONDARY, ...)
    
    def extract_pois(self):
        yield POI(osm_id=100, category=POICategory.FOOD, ...)
    
    def extract_zones(self):
        yield Zone(osm_id=200, zone_type="region", ...)


class FakeRepository(GeoRepository):
    """Fake storage for testing."""
    
    def __init__(self):
        self.saved_roads = []
        self.saved_pois = []
        self.saved_zones = []
    
    async def save_roads(self, roads):
        self.saved_roads.extend(roads)
    
    async def save_pois(self, pois):
        self.saved_pois.extend(pois)
    
    async def save_zones(self, zones):
        self.saved_zones.extend(zones)


# Test the use case
async def test_pipeline():
    extractor = FakeExtractor()
    repository = FakeRepository()
    
    pipeline = RunPipelineUseCase(extractor, repository, batch_size=10)
    await pipeline.execute()
    
    # Verify it worked
    assert len(repository.saved_roads) == 2
    assert len(repository.saved_pois) == 1
    assert len(repository.saved_zones) == 1
```

No real database or OSM file needed!

## Key Principles

### 1. Dependency Inversion
The Application Layer defines what it needs (ports). The Infrastructure Layer provides implementations.

### 2. Single Responsibility
Each use case has one clear purpose:
- RunPipelineUseCase: Import data
- (Future) FindNearbyPOIsUseCase: Search for POIs
- (Future) CalculateRouteUseCase: Find best route

### 3. Coordination, Not Implementation
The Application Layer coordinates but doesn't implement details:
- ✅ "Extract roads, batch them, save them"
- ❌ "Read bytes from .pbf file, parse protobuf, execute SQL INSERT"

## Summary

The Application Layer:

**Contains:**
- **Ports** - Interfaces defining what Infrastructure must provide
- **Use Cases** - Workflows that coordinate domain and infrastructure

**Responsibilities:**
- Orchestrate the flow of data
- Batch operations for efficiency
- Define clear interfaces for infrastructure

**Does NOT:**
- Know about specific technologies (PostgreSQL, OSM format, etc.)
- Contain business logic (that's in Domain)
- Directly access files or databases (that's in Infrastructure)

**Benefits:**
- Easy to test (use fake implementations)
- Easy to change infrastructure (swap databases)
- Clear separation of concerns
- Follows SOLID principles
