# Domain Layer

## What is the Domain Layer?

The Domain Layer is the heart of the Chorographer application. It contains all the core business logic and rules about roads, points of interest, and zones in Madagascar. Think of it as the "brain" that knows what a road is, what makes a good or bad road surface, and how to calculate travel penalties.

## Why is it Special?

The Domain Layer is completely independent. It doesn't know about:
- Where the data comes from (OpenStreetMap files)
- Where the data goes (PostgreSQL database)
- How the data is logged
- Configuration files

This makes it very easy to test and change. You can test the business logic without needing a database or real data files.

## What's Inside?

The Domain Layer has four main parts:

### 1. Entities
Real-world things that have an identity and can change over time:
- **Road** - A street, highway, or path
- **POI (Point of Interest)** - A place like a gas station, hotel, or restaurant
- **Zone** - An administrative area like a region or district
- **Segment** - A piece of a road used for route planning

### 2. Value Objects
Simple pieces of information that don't have their own identity:
- **Coordinates** - A location (latitude and longitude)
- **Address** - A street address
- **RoadPenalty** - Information about how road conditions affect travel speed
- **OperatingHours** - When a business is open

### 3. Enums
Lists of allowed values for certain properties:
- **RoadType** - Types of roads (primary, secondary, residential, etc.)
- **Surface** - What the road is made of (asphalt, gravel, dirt, etc.)
- **Smoothness** - How smooth the road is to drive on
- **POICategory** - Types of places (transport, food, lodging, etc.)

### 4. Exceptions
Custom error messages when something goes wrong in the business logic.

## Key Principles

### Pure Business Logic
Everything in the Domain Layer is about the real-world concepts, not technical details. For example:
- We say "Road" not "DatabaseRow"
- We say "Coordinates" not "LatLonTuple"
- We calculate penalties based on surface quality, not database queries

### No External Dependencies
The Domain Layer only uses standard Python. No third-party libraries. This means:
- It's fast to load
- It's easy to understand
- It's simple to test
- It won't break if we change databases or file formats

### Immutability Where Appropriate
Value Objects (like Coordinates or Address) cannot be changed after creation. This prevents bugs and makes the code safer.

## How Other Layers Use It

```
┌─────────────────────────────────────────┐
│         Infrastructure Layer            │
│  (OSM files, PostgreSQL, Config)        │
│                                         │
│  Creates Domain objects from OSM data   │
│  Saves Domain objects to database       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         Application Layer               │
│  (Use Cases, Ports)                     │
│                                         │
│  Orchestrates the Domain objects        │
│  Defines what Infrastructure must do    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         Domain Layer                    │
│  (Entities, Value Objects, Enums)       │
│                                         │
│  Pure business logic and rules          │
└─────────────────────────────────────────┘
```

## Example Usage

Here's how you might create a Road in the Domain Layer:

```python
from domain.entities import Road
from domain.enums.road import RoadType, Surface, Smoothness
from domain.value_objects import Coordinates, RoadPenalty

# Create a road
road = Road(
    id=12345,
    geometry=[
        Coordinates(lat=-18.8792, lon=47.5079),
        Coordinates(lat=-18.8800, lon=47.5090)
    ],
    road_type=RoadType.PRIMARY,
    surface=Surface.ASPHALT,
    smoothness=Smoothness.GOOD,
    name="Route Nationale 1",
    lanes=2,
    oneway=False,
    max_speed=80
)

# Calculate the penalty for this road
penalty = RoadPenalty.from_road_attributes(
    surface=road.surface,
    smoothness=road.smoothness,
    is_rainy_season=True
)

# The effective speed would be: 80 km/h × penalty factors
```

## Testing the Domain

Because the Domain Layer has no external dependencies, testing is straightforward:

```python
def test_road_penalty_on_dirt_road():
    penalty = RoadPenalty(
        surface_factor=0.4,  # Dirt road
        smoothness_factor=0.6,  # Bad smoothness
        rainy_season_factor=0.6  # Rainy season
    )
    
    base_speed = 60  # km/h
    effective_speed = base_speed * penalty.total_factor()
    
    # Dirt road in rain = much slower
    assert effective_speed < 20  # About 14.4 km/h
```

## Summary

The Domain Layer is:
- **Independent** - Doesn't rely on external systems
- **Pure** - Only contains business logic
- **Testable** - Easy to test without infrastructure
- **Clear** - Uses real-world language and concepts
- **Stable** - Rarely changes because business rules are stable

It represents what the application does, not how it does it.
