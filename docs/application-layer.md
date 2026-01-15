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

## Two Main Components

### 1. Ports (Interfaces)

Ports are like contracts that define what the Infrastructure must do, without saying how to do it.

Think of a port as a job description:
- "We need someone who can extract road data"
- "We need someone who can save data to a database"

The Infrastructure Layer provides the actual implementations (the "employees who do the job").

### 2. Use Cases

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

## Use Cases Explained

### What are Use Cases?

Use Cases implement specific business workflows. Each use case:
1. Takes input (parameters)
2. Uses ports to interact with infrastructure
3. Coordinates domain logic
4. Returns output or performs actions

### The Main Use Case: RunPipeline

This is the primary use case that imports OpenStreetMap data into the database.

#### What It Does

```
1. Extract roads from OSM file
2. Batch them (group into sets of 1000)
3. Save each batch to database
4. Repeat for POIs
5. Repeat for Zones
6. Log progress throughout
```

#### The Code Structure

```python
from application.ports import DataExtractor, GeoRepository

class RunPipelineUseCase:
    """
    Use case for running the complete data import pipeline.
    
    Reads geographic data from a source and saves it to a repository.
    """
    
    def __init__(
        self,
        extractor: DataExtractor,
        repository: GeoRepository,
        batch_size: int = 1000
    ):
        """
        Initialize the use case.
        
        Args:
            extractor: Data source (implements DataExtractor port)
            repository: Data storage (implements GeoRepository port)
            batch_size: How many items to save at once
        """
        self.extractor = extractor
        self.repository = repository
        self.batch_size = batch_size
    
    async def execute(self) -> None:
        """
        Run the complete pipeline.
        
        1. Import all roads
        2. Import all POIs
        3. Import all zones
        """
        await self._import_roads()
        await self._import_pois()
        await self._import_zones()
    
    async def _import_roads(self) -> None:
        """Import roads in batches."""
        batch = []
        
        for road in self.extractor.extract_roads():
            batch.append(road)
            
            if len(batch) >= self.batch_size:
                await self.repository.save_roads(batch)
                batch = []
        
        # Save remaining items
        if batch:
            await self.repository.save_roads(batch)
    
    async def _import_pois(self) -> None:
        """Import POIs in batches."""
        # Similar to _import_roads
        ...
    
    async def _import_zones(self) -> None:
        """Import zones in batches."""
        # Similar to _import_roads
        ...
```

#### How It Works

**Dependency Injection:**
The use case receives its dependencies (extractor, repository) from outside. This means:
- It doesn't know if data comes from OSM or GeoJSON
- It doesn't know if data goes to PostgreSQL or SQLite
- It just knows the interfaces (ports)

**Batching:**
Instead of saving one road at a time, we batch them:
```
Collect 1000 roads → Save all at once → Collect next 1000 → Repeat
```

This is much faster than individual saves.

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
    pbf_reader = PBFReader(settings.OSM_FILE_PATH)
    extractor = OSMExtractor(pbf_reader)  # Implements DataExtractor port
    
    # Data storage (PostgreSQL)
    pool = await create_pool(settings)
    repository = PostgresWriter(pool)  # Implements GeoRepository port
    
    # 2. Create the use case with dependencies
    pipeline = RunPipelineUseCase(
        extractor=extractor,
        repository=repository,
        batch_size=settings.BATCH_SIZE
    )
    
    # 3. Run it!
    await pipeline.execute()
    
    print("Pipeline complete!")

# Run the async main function
asyncio.run(main())
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
        yield Zone(osm_id=200, admin_level=AdminLevel.REGION, ...)


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
