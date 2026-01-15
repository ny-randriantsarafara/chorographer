# OSM Component

## What is the OSM Component?

The OSM Component reads OpenStreetMap data files and converts them into clean, usable Domain entities (Roads, POIs, Zones). It's like a translator that converts OpenStreetMap's specific format into the language our application understands.

## What is OpenStreetMap?

OpenStreetMap (OSM) is a free, collaborative map of the world. Anyone can contribute data about:
- Roads and paths
- Buildings and addresses
- Points of interest (restaurants, gas stations, etc.)
- Administrative boundaries (countries, regions, districts)

OSM data is stored in a special format called **PBF** (Protocolbuffer Binary Format) - a compressed, efficient format for storing map data.

## Why Do We Need This Component?

Raw OSM data is:
- Complex (nested structures, special tags)
- Inconsistent (different mappers use different conventions)
- Large (Madagascar's .pbf file is hundreds of megabytes)

The OSM Component handles all this complexity so the rest of the application can work with simple, clean Domain entities.

## The Files

```
infrastructure/osm/
├── reader.py        # Reads raw bytes from .pbf files
├── extractor.py     # Main component: converts OSM → Domain
├── transformers.py  # Converts OSM tags → Domain enums/values
├── handlers.py      # Osmium handlers for nodes, ways, relations
└── types.py         # Data structures for raw OSM data
```

---

## How It Works: The Big Picture

```
┌─────────────────┐
│ madagascar.pbf  │  OpenStreetMap file (300+ MB)
└────────┬────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ PBFReader (reader.py)                  │
│ - Opens file                           │
│ - Reads nodes, ways, relations         │
│ - Collects node coordinates            │
└──────────┬─────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ Handlers (handlers.py)                 │
│ - NodeHandler: collects coordinates    │
│ - WayHandler: collects way data        │
│ - RelationHandler: collects boundaries │
└──────────┬─────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ OSMExtractor (extractor.py)            │
│ - Filters relevant data                │
│ - Converts to Domain entities          │
│ - Uses transformers for tag conversion │
└──────────┬─────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ Domain Entities                        │
│ Road, POI, Zone objects                │
└────────────────────────────────────────┘
```

---

## Component 1: PBFReader

**Purpose:** Read raw data from .pbf files using the osmium library.

### What It Does

1. Opens the .pbf file
2. Makes two passes through the file:
   - **First pass:** Collect all node coordinates
   - **Second pass:** Read ways and relations
3. Yields raw data structures (RawNode, RawWay, RawRelation)

### Why Two Passes?

In OSM, a road (called a "way") is stored as:
```
Way 12345:
  tags: highway=primary, name=RN7
  nodes: [100, 101, 102, 103]  # Just IDs!
```

The actual coordinates are stored separately:
```
Node 100: lat=-18.8792, lon=47.5079
Node 101: lat=-18.8800, lon=47.5090
...
```

So we need to:
1. **First pass:** Read all nodes, remember their coordinates
2. **Second pass:** Read ways, look up coordinates for each node ID

### Example Usage

```python
from pathlib import Path
from infrastructure.osm import PBFReader

# Open the file
reader = PBFReader(Path("data/madagascar-latest.osm.pbf"))

# Get all ways (roads, buildings, etc.)
for raw_way in reader.ways():
    print(f"Way {raw_way.id}: {raw_way.tags}")
    print(f"Coordinates: {raw_way.coordinates}")
```

### Memory Management

The reader is a **generator** - it yields one item at a time instead of loading everything into memory:

```python
# ❌ This would use too much memory
all_ways = list(reader.ways())  # Millions of ways!

# ✅ This processes one at a time
for way in reader.ways():
    process(way)  # Only one in memory at a time
```

---

## Component 2: Handlers

**Purpose:** Low-level handlers that work with osmium to collect data.

### Three Handler Types

#### NodeHandler
Collects node coordinates during the first pass.

```python
class NodeHandler:
    """
    Collects coordinates for all nodes.
    
    Stores: node_id → (lat, lon)
    """
    
    def __init__(self):
        self.node_locations = {}  # {node_id: (lat, lon)}
    
    def node(self, n):
        """Called for each node in the file."""
        self.node_locations[n.id] = (n.location.lat, n.location.lon)
```

#### WayHandler
Collects way data (roads, buildings, etc.).

```python
class WayHandler:
    """
    Collects ways (linear features like roads).
    """
    
    def __init__(self, node_locations):
        self.node_locations = node_locations
        self.ways = []
    
    def way(self, w):
        """Called for each way in the file."""
        # Get coordinates for this way
        coords = [
            self.node_locations[node.ref]
            for node in w.nodes
            if node.ref in self.node_locations
        ]
        
        # Store as RawWay
        self.ways.append(RawWay(
            id=w.id,
            tags=dict(w.tags),
            coordinates=coords
        ))
```

#### RelationHandler
Collects relations (boundaries, multipolygons, etc.).

```python
class RelationHandler:
    """
    Collects relations (complex features like administrative boundaries).
    """
    
    def relation(self, r):
        """Called for each relation in the file."""
        # Relations can contain ways or other relations
        # We mainly use them for administrative boundaries
        ...
```

---

## Component 3: Transformers

**Purpose:** Convert OSM-specific tag values to Domain enums and value objects.

### Why Transformers?

OSM uses string tags like:
- `highway=primary`
- `surface=asphalt`
- `smoothness=bad`

We need to convert these to type-safe Domain enums:
- `RoadType.PRIMARY`
- `Surface.ASPHALT`
- `Smoothness.BAD`

### Example Transformers

#### RoadTypeTransformer

```python
class RoadTypeTransformer:
    """
    Converts OSM highway tag to RoadType enum.
    """
    
    # Mapping from OSM values to our enums
    OSM_TO_DOMAIN = {
        "motorway": RoadType.MOTORWAY,
        "trunk": RoadType.TRUNK,
        "primary": RoadType.PRIMARY,
        "secondary": RoadType.SECONDARY,
        "tertiary": RoadType.TERTIARY,
        "residential": RoadType.RESIDENTIAL,
        "unclassified": RoadType.UNCLASSIFIED,
        "track": RoadType.TRACK,
        "path": RoadType.PATH,
    }
    
    @classmethod
    def from_osm(cls, highway_tag: str) -> RoadType:
        """
        Convert OSM highway tag to RoadType.
        
        Args:
            highway_tag: Value from OSM (e.g., "primary")
        
        Returns:
            RoadType enum value
        """
        return cls.OSM_TO_DOMAIN.get(
            highway_tag,
            RoadType.UNCLASSIFIED  # Default if unknown
        )
```

Usage:
```python
osm_highway = "primary"
road_type = RoadTypeTransformer.from_osm(osm_highway)
# Result: RoadType.PRIMARY
```

#### SurfaceTransformer

```python
class SurfaceTransformer:
    """
    Converts OSM surface tag to Surface enum.
    """
    
    OSM_TO_DOMAIN = {
        "asphalt": Surface.ASPHALT,
        "paved": Surface.PAVED,
        "concrete": Surface.CONCRETE,
        "gravel": Surface.GRAVEL,
        "dirt": Surface.DIRT,
        "earth": Surface.DIRT,
        "ground": Surface.GROUND,
        "sand": Surface.SAND,
        "unpaved": Surface.UNPAVED,
    }
    
    @classmethod
    def from_osm(cls, surface_tag: str | None) -> Surface:
        if surface_tag is None:
            return Surface.UNKNOWN
        
        # Normalize to lowercase
        surface_tag = surface_tag.lower()
        
        return cls.OSM_TO_DOMAIN.get(
            surface_tag,
            Surface.UNKNOWN
        )
```

#### AddressTransformer

```python
class AddressTransformer:
    """
    Converts OSM addr:* tags to Address value object.
    """
    
    @classmethod
    def from_osm(cls, tags: dict) -> Address | None:
        """
        Build Address from OSM tags.
        
        OSM uses tags like:
        - addr:street
        - addr:housenumber
        - addr:city
        - addr:postcode
        """
        # Extract address components
        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        city = tags.get("addr:city")
        postcode = tags.get("addr:postcode")
        
        # Only create Address if we have at least one component
        if not any([street, housenumber, city, postcode]):
            return None
        
        return Address(
            street=street,
            housenumber=housenumber,
            city=city,
            postcode=postcode
        )
```

---

## Component 4: OSMExtractor

**Purpose:** Main component that ties everything together. Implements the DataExtractor port.

### What It Does

1. Uses PBFReader to get raw OSM data
2. Filters for relevant items (roads, POIs, zones)
3. Uses Transformers to convert OSM data to Domain types
4. Yields Domain entities

### Example: Extracting Roads

```python
class OSMExtractor(DataExtractor):
    """
    Extracts Domain entities from OSM data.
    """
    
    def __init__(self, pbf_reader: PBFReader):
        self.reader = pbf_reader
    
    def extract_roads(self) -> Iterator[Road]:
        """
        Extract all roads from OSM data.
        
        Yields:
            Road entities
        """
        for raw_way in self.reader.ways():
            # Check if this way is a road
            if not self._is_road(raw_way):
                continue
            
            # Convert to Road entity
            road = self._convert_to_road(raw_way)
            yield road
    
    def _is_road(self, raw_way: RawWay) -> bool:
        """
        Check if a way represents a road.
        
        In OSM, roads have a 'highway' tag.
        """
        return "highway" in raw_way.tags
    
    def _convert_to_road(self, raw_way: RawWay) -> Road:
        """
        Convert raw OSM way to Road entity.
        """
        tags = raw_way.tags
        
        # Convert coordinates
        geometry = [
            Coordinates(lat=lat, lon=lon)
            for lat, lon in raw_way.coordinates
        ]
        
        # Convert tags to domain types
        road_type = RoadTypeTransformer.from_osm(tags["highway"])
        surface = SurfaceTransformer.from_osm(tags.get("surface"))
        smoothness = SmoothnessTransformer.from_osm(tags.get("smoothness"))
        
        # Extract other properties
        name = tags.get("name")
        lanes = int(tags.get("lanes", 2))
        oneway = tags.get("oneway") == "yes"
        max_speed = self._parse_maxspeed(tags.get("maxspeed"))
        
        return Road(
            osm_id=raw_way.id,
            geometry=geometry,
            road_type=road_type,
            surface=surface,
            smoothness=smoothness,
            name=name,
            lanes=lanes,
            oneway=oneway,
            max_speed=max_speed,
            tags=tags  # Keep raw tags for reference
        )
    
    def _parse_maxspeed(self, maxspeed_tag: str | None) -> int | None:
        """
        Parse maxspeed tag to integer.
        
        OSM uses values like:
        - "50" → 50
        - "50 km/h" → 50
        - "30 mph" → convert to km/h
        """
        if maxspeed_tag is None:
            return None
        
        # Remove common suffixes
        maxspeed_tag = maxspeed_tag.replace(" km/h", "")
        maxspeed_tag = maxspeed_tag.replace("km/h", "")
        
        try:
            return int(maxspeed_tag)
        except ValueError:
            return None
```

### Example: Extracting POIs

```python
def extract_pois(self) -> Iterator[POI]:
    """
    Extract all points of interest from OSM data.
    
    POIs can be:
    - Nodes with amenity/shop tags
    - Small buildings (ways)
    """
    # Extract from nodes
    for raw_node in self.reader.nodes():
        if self._is_poi(raw_node.tags):
            poi = self._convert_to_poi(
                osm_id=raw_node.id,
                coordinates=Coordinates(raw_node.lat, raw_node.lon),
                tags=raw_node.tags
            )
            yield poi

def _is_poi(self, tags: dict) -> bool:
    """
    Check if tags indicate a POI.
    
    POIs usually have amenity, shop, or tourism tags.
    """
    return any(key in tags for key in ["amenity", "shop", "tourism"])

def _convert_to_poi(
    self,
    osm_id: int,
    coordinates: Coordinates,
    tags: dict
) -> POI:
    """Convert OSM data to POI entity."""
    
    # Determine category and subcategory
    category, subcategory = POICategoryTransformer.from_osm(tags)
    
    # Extract other properties
    name = tags.get("name")
    address = AddressTransformer.from_osm(tags)
    phone = tags.get("phone")
    opening_hours = tags.get("opening_hours")
    website = tags.get("website")
    
    return POI(
        osm_id=osm_id,
        coordinates=coordinates,
        category=category,
        subcategory=subcategory,
        name=name,
        address=address,
        phone=phone,
        opening_hours=opening_hours,
        website=website,
        tags=tags
    )
```

---

## Component 5: Types

**Purpose:** Define data structures for raw OSM data (before conversion to Domain).

```python
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class RawNode:
    """
    Raw node data from OSM.
    
    Nodes are points on the map.
    """
    id: int
    lat: float
    lon: float
    tags: Dict[str, str]

@dataclass
class RawWay:
    """
    Raw way data from OSM.
    
    Ways are linear features (roads, building outlines, etc.).
    """
    id: int
    tags: Dict[str, str]
    coordinates: List[Tuple[float, float]]  # [(lat, lon), ...]

@dataclass
class RawRelation:
    """
    Raw relation data from OSM.
    
    Relations are collections of nodes/ways (boundaries, routes, etc.).
    """
    id: int
    tags: Dict[str, str]
    members: List[Dict]  # Members can be nodes, ways, or other relations
```

These are simple data containers - no business logic, just data.

---

## The Complete Flow

Here's how a road goes from .pbf file to Road entity:

```
1. PBF File
   └─ Way 12345
      ├─ tags: {highway: "primary", name: "RN7", surface: "asphalt"}
      └─ nodes: [100, 101, 102]

2. PBFReader (First Pass)
   └─ NodeHandler collects:
      ├─ Node 100: (-18.8792, 47.5079)
      ├─ Node 101: (-18.8800, 47.5090)
      └─ Node 102: (-18.8810, 47.5100)

3. PBFReader (Second Pass)
   └─ WayHandler creates:
      RawWay(
          id=12345,
          tags={highway: "primary", name: "RN7", surface: "asphalt"},
          coordinates=[(-18.8792, 47.5079), (-18.8800, 47.5090), (-18.8810, 47.5100)]
      )

4. OSMExtractor filters and converts:
   └─ _is_road(raw_way) → True (has "highway" tag)
   └─ _convert_to_road(raw_way):
      ├─ RoadTypeTransformer: "primary" → RoadType.PRIMARY
      ├─ SurfaceTransformer: "asphalt" → Surface.ASPHALT
      └─ Create Coordinates objects

5. Final Result:
   Road(
       osm_id=12345,
       geometry=[
           Coordinates(lat=-18.8792, lon=47.5079),
           Coordinates(lat=-18.8800, lon=47.5090),
           Coordinates(lat=-18.8810, lon=47.5100)
       ],
       road_type=RoadType.PRIMARY,
       surface=Surface.ASPHALT,
       name="RN7",
       ...
   )
```

---

## Performance Considerations

### 1. Streaming
Process one item at a time, don't load everything:
```python
# ✅ Good - yields one at a time
for road in extractor.extract_roads():
    process(road)

# ❌ Bad - loads millions into memory
all_roads = list(extractor.extract_roads())
```

### 2. Two-Pass Requirement
We must make two passes because:
- Ways reference nodes by ID only
- Node coordinates are stored separately
- We can't know all coordinates in advance

### 3. Memory-Mapped Files
The osmium library uses memory-mapped files for efficiency - it doesn't load the whole file into RAM.

---

## Error Handling

### Missing Data
```python
# Some ways might reference nodes we don't have
coords = [
    self.node_locations[node_id]
    for node_id in way.nodes
    if node_id in self.node_locations  # Skip missing nodes
]

if len(coords) < 2:
    # Not enough points for a line
    return None
```

### Invalid Tags
```python
# Some tags might be invalid
try:
    lanes = int(tags.get("lanes", 2))
except ValueError:
    lanes = 2  # Use default if invalid
```

### Missing Required Data
```python
if "highway" not in tags:
    # Not a road, skip it
    return None
```

---

## Summary

The OSM Component:

**Purpose:**
- Read OpenStreetMap .pbf files
- Convert OSM data to Domain entities
- Handle OSM-specific complexity

**Components:**
- **PBFReader** - Reads raw .pbf file data
- **Handlers** - Collect nodes, ways, relations
- **Transformers** - Convert OSM tags to Domain types
- **OSMExtractor** - Main orchestrator, implements DataExtractor port
- **Types** - Data structures for raw OSM data

**Key Features:**
- Two-pass reading (for node coordinates)
- Streaming (one item at a time)
- Filtering (only relevant data)
- Transformation (OSM → Domain)

**Benefits:**
- Isolates OSM complexity
- Provides clean Domain entities
- Memory efficient
- Handles large files (100+ MB)
