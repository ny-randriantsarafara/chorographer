# Domain Entities

## What are Entities?

Entities are the main "things" in our application that have a unique identity. Think of them like real-world objects that you can identify and track over time. For example, a specific road in Antananarivo has an identity (its OpenStreetMap ID) and properties that might change (like its surface condition).

## The Four Main Entities

### 1. Road

A Road represents any kind of path you can drive or walk on - from major highways to small dirt tracks.

#### What Information Does a Road Have?

| Field | What It Means | Example |
|-------|---------------|---------|
| `id` | Unique number from OpenStreetMap | 123456 |
| `geometry` | List of coordinates that draw the road on a map | [(lat, lon), (lat, lon), ...] |
| `road_type` | What kind of road it is | Primary highway, residential street, dirt track |
| `surface` | What the road is made of | Asphalt, gravel, dirt, sand |
| `smoothness` | How smooth it is to drive on | Excellent, good, bad, horrible |
| `name` | The road's name if it has one | "Route Nationale 1" |
| `lanes` | How many lanes it has | 2 (default if not specified) |
| `oneway` | Can you only drive in one direction? | True or False |
| `max_speed` | Speed limit in kilometers per hour | 80 |
| `tags` | All the raw data from OpenStreetMap | {"highway": "primary", "ref": "RN1"} |

#### Why Roads are Important

Roads are the foundation of route planning. We need to know:
- Where the road goes (geometry)
- What condition it's in (surface, smoothness)
- How fast you can drive on it (max_speed, road_type)
- Any restrictions (oneway)

#### Example

```python
road = Road(
    id=987654,
    geometry=[
        Coordinates(lat=-18.8792, lon=47.5079),
        Coordinates(lat=-18.8800, lon=47.5090),
        Coordinates(lat=-18.8810, lon=47.5100)
    ],
    road_type=RoadType.PRIMARY,
    surface=Surface.ASPHALT,
    smoothness=Smoothness.GOOD,
    name="Route Nationale 7",
    lanes=2,
    oneway=False,
    max_speed=80,
    tags={"highway": "primary", "surface": "asphalt"}
)
```

---

### 2. POI (Point of Interest)

A POI is any place that might be useful for travelers - gas stations, hotels, restaurants, hospitals, etc.

#### What Information Does a POI Have?

| Field | What It Means | Example |
|-------|---------------|---------|
| `id` | Unique number from OpenStreetMap | 456789 |
| `coordinates` | Exact location | (-18.8792, 47.5079) |
| `category` | General type of place | Transport, Food, Lodging, Health |
| `subcategory` | Specific type | fuel, restaurant, hotel, pharmacy |
| `name` | Business or place name | "Total Gas Station" |
| `address` | Street address if available | "Avenue de l'Indépendance" |
| `phone` | Contact phone number | "+261 20 22 123 45" |
| `opening_hours` | When the place is open | "Mo-Fr 08:00-18:00" |
| `price_range` | How expensive (1-4 scale) | 2 (moderate) |
| `website` | Web address | "https://example.com" |
| `name_normalized` | Normalized name for search | "total gas station" |
| `search_text` | Search string built from name/brand/etc. | "Total Gas Station Total" |
| `search_text_normalized` | Normalized search text | "total gas station total" |
| `has_name` | Whether the POI has a name | True |
| `popularity` | Ranking score (higher = more popular) | 0 |
| `tags` | All the raw data from OpenStreetMap | {"amenity": "fuel", "brand": "Total"} |

#### Why POIs are Important

When planning a trip, you need to know:
- Where can I get gas?
- Where can I sleep?
- Where can I eat?
- Where is the nearest hospital?

POIs answer these questions.

#### Example

```python
poi = POI(
    id=111222,
    coordinates=Coordinates(lat=-18.9100, lon=47.5200),
    category=POICategory.TRANSPORT,
    subcategory="fuel",
    name="Station Total Andranomena",
    address=Address(
        street="Avenue de l'Indépendance",
        housenumber="25",
        city="Antananarivo"
    ),
    phone="+261 20 22 123 45",
    opening_hours=OperatingHours("Mo-Su 06:00-22:00"),
    tags={"amenity": "fuel", "brand": "Total"}
)
```

---

### 3. Zone

A Zone is an administrative boundary - like a country, region, district, or town.

#### What Information Does a Zone Have?

| Field | What It Means | Example |
|-------|---------------|---------|
| `id` | Unique number from OpenStreetMap | 789012 |
| `geometry` | List of coordinates that draw the boundary | [(lat, lon), (lat, lon), ...] |
| `zone_type` | What level of government | country, region, district, commune, fokontany |
| `name` | Official name | "Analamanga" |
| `iso_code` | International code | "MG-T" |
| `population` | How many people live there | 3,618,128 |
| `level` | Hierarchy level (0-4) | 1 |
| `parent_zone_id` | Parent zone ID (if any) | 1 |
| `tags` | All the raw data from OpenStreetMap | {"admin_level": "4", "name": "Analamanga"} |

Localized names like `name:mg` remain available in `tags` if you need them.

#### Zone Types Explained

Derived from OSM `admin_level` tags:

- **country**: Level 2 (Madagascar)
- **region**: Level 4 (Faritra)
- **district**: Level 6 (Distrika)
- **commune**: Level 8 (Kaominina)
- **fokontany**: Level 10 (smallest administrative unit)

#### Why Zones are Important

Zones help us:
- Organize geographic data by region
- Calculate statistics (like "how many hotels in Analamanga?")
- Determine which administrative area a point is in
- Plan routes that respect administrative boundaries

#### Example

```python
zone = Zone(
    id=445566,
    geometry=[
        Coordinates(lat=-18.7000, lon=47.3000),
        Coordinates(lat=-18.7000, lon=47.7000),
        Coordinates(lat=-19.1000, lon=47.7000),
        Coordinates(lat=-19.1000, lon=47.3000),
        Coordinates(lat=-18.7000, lon=47.3000)  # Close the polygon
    ],
    zone_type="region",
    name="Analamanga",
    level=1,
    parent_zone_id=1,
    iso_code="MG-T",
    population=3618128,
    tags={"admin_level": "4", "name": "Analamanga"}
)
```

---

### 4. Segment

A Segment is a piece of a road, used for building a routing graph. While a Road might be 10 kilometers long, we break it into smaller Segments at intersections.

#### What Information Does a Segment Have?

| Field | What It Means | Example |
|-------|---------------|---------|
| `id` | Unique number for this segment | 1001 |
| `road_id` | Which road this segment belongs to | 987654 |
| `start` | Starting point | (-18.8792, 47.5079) |
| `end` | Ending point | (-18.8800, 47.5090) |
| `length` | How long in meters | 125.5 |
| `penalty` | Speed reduction factors | Surface, smoothness, weather |
| `oneway` | One-way restriction | True or False |
| `base_speed` | Speed limit or default speed | 50 km/h |

#### Why Segments are Important

Segments are used for route calculation:
1. Break long roads into smaller pieces at intersections
2. Each segment has a cost (time = length / effective_speed)
3. Routing algorithms find the cheapest path through segments

#### How Effective Speed is Calculated

```
effective_speed = base_speed × surface_factor × smoothness_factor × season_factor

Example:
- base_speed = 60 km/h
- surface_factor = 0.7 (gravel road)
- smoothness_factor = 0.6 (bad condition)
- season_factor = 0.6 (rainy season)
- effective_speed = 60 × 0.7 × 0.6 × 0.6 = 15.12 km/h
```

#### Example

```python
segment = Segment(
    id=5001,
    road_id=987654,
    start=Coordinates(lat=-18.8792, lon=47.5079),
    end=Coordinates(lat=-18.8800, lon=47.5090),
    length=125.5,  # meters
    penalty=RoadPenalty(
        surface_factor=1.0,  # Asphalt
        smoothness_factor=0.9,  # Good
        rainy_season_factor=1.0  # Not affected by rain
    ),
    oneway=False,
    base_speed=80  # km/h
)
```

---

## How Entities Relate to Each Other

```
┌─────────────┐
│    Zone     │  Administrative area
└──────┬──────┘
       │ contains
       ▼
┌─────────────┐         ┌──────────────┐
│    Road     │◄────────│   Segment    │  Pieces of roads
└──────┬──────┘ part of └──────────────┘
       │
       │ near
       ▼
┌─────────────┐
│     POI     │  Points along roads
└─────────────┘
```

## Key Differences: Entity vs Value Object

**Entity (like Road):**
- Has a unique identity (id)
- Can change over time (surface might be repaired)
- Two roads are the same if they have the same id

**Value Object (like Coordinates):**
- No unique identity
- Never changes after creation
- Two coordinates are the same if they have the same lat/lon values

## Summary

Entities are the core objects in our domain:
- **Road** - Paths for traveling
- **POI** - Useful places for travelers
- **Zone** - Administrative boundaries
- **Segment** - Road pieces for route calculation

Each entity has a unique identity and represents a real-world concept that our application needs to track and manage.
