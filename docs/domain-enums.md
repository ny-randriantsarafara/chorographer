# Domain Enums

## What are Enums?

Enums (short for "enumerations") are lists of allowed values for certain properties. They prevent mistakes by limiting choices to only valid options.

Think of it like a multiple-choice question - you can only pick from the provided options, not make up your own answer.

## Why Use Enums?

### 1. Prevent Typos

```python
# Without enum - easy to make mistakes
road.surface = "ashpalt"  # Typo! Should be "asphalt"
road.surface = "Gravel"   # Wrong case
road.surface = "rocks"    # Not a valid surface type

# With enum - catches errors immediately
road.surface = Surface.ASPHALT  # Correct
road.surface = Surface.ROCKS    # Error! ROCKS doesn't exist
```

### 2. Clear Documentation

When you see `surface: Surface`, you know exactly what values are allowed. You can look at the Surface enum to see all options.

### 3. IDE Support

Your code editor can suggest all valid options when you type `Surface.`

## The Four Main Enums

### 1. RoadType

Defines the different types of roads based on importance and usage.

#### Available Values

| Value | What It Means | Typical Use |
|-------|---------------|-------------|
| `MOTORWAY` | High-speed highway, usually tolled | Only in major cities or key routes |
| `TRUNK` | Important road connecting major cities | Main national routes |
| `PRIMARY` | Major road (often called "Route Nationale") | RN1, RN2, RN7, etc. |
| `SECONDARY` | Regional road connecting towns | Less busy than primary |
| `TERTIARY` | Local road connecting villages | Smaller communities |
| `UNCLASSIFIED` | Minor public road | Not formally classified |
| `RESIDENTIAL` | Street in a residential area | Neighborhoods |
| `TRACK` | Agricultural or forest track | Often unpaved, for farm vehicles |
| `PATH` | Narrow path for walking or biking | Usually not for cars |

#### Usage Example

```python
from domain.enums.road import RoadType

# Route Nationale 7 is a primary road
rn7 = Road(
    road_type=RoadType.PRIMARY,
    name="Route Nationale 7"
)

# A village street
village_street = Road(
    road_type=RoadType.TERTIARY,
    name="Rue du Village"
)

# A dirt track to a farm
farm_track = Road(
    road_type=RoadType.TRACK,
    name=None  # Often unnamed
)
```

#### Speed Estimates by Type

Different road types have different default speeds:
- `MOTORWAY`: 100-110 km/h
- `TRUNK`: 90-100 km/h
- `PRIMARY`: 80-90 km/h
- `SECONDARY`: 60-80 km/h
- `TERTIARY`: 50-60 km/h
- `RESIDENTIAL`: 30-50 km/h
- `TRACK`: 20-40 km/h
- `PATH`: 5-15 km/h (walking/biking)

---

### 2. Surface

Defines what material the road is made of.

#### Available Values

| Value | Description | Common in Madagascar |
|-------|-------------|---------------------|
| `ASPHALT` | Black tar surface, smooth | Major roads in cities |
| `PAVED` | Any paved surface (generic) | When specific type unknown |
| `CONCRETE` | Concrete slabs | Some urban roads |
| `GRAVEL` | Crushed stone | Common in rural areas |
| `DIRT` | Compacted earth | Very common outside cities |
| `SAND` | Sandy surface | Beach areas, desert regions |
| `UNPAVED` | Not paved (generic) | When specific type unknown |
| `GROUND` | Natural ground | Paths through fields |
| `UNKNOWN` | No information available | When OSM data is missing |

#### Usage Example

```python
from domain.enums.road import Surface

# Antananarivo city center - asphalt
city_road = Road(
    surface=Surface.ASPHALT,
    name="Avenue de l'Indépendance"
)

# Rural road - gravel
rural_road = Road(
    surface=Surface.GRAVEL,
    name="Route vers Ambohimanga"
)

# Very rural - dirt
village_road = Road(
    surface=Surface.DIRT
)
```

#### How Surface Affects Speed

Surface directly impacts travel speed through the `surface_factor`:

```python
Surface.ASPHALT   → factor = 1.0  (full speed)
Surface.CONCRETE  → factor = 0.95 (nearly full speed)
Surface.GRAVEL    → factor = 0.7  (30% slower)
Surface.DIRT      → factor = 0.4  (60% slower)
Surface.SAND      → factor = 0.3  (70% slower)
```

---

### 3. Smoothness

Describes the physical condition of the road surface.

#### Available Values

| Value | What It Means | Description |
|-------|---------------|-------------|
| `EXCELLENT` | Perfect condition | Like new, very smooth |
| `GOOD` | Minor imperfections | Some wear but comfortable |
| `INTERMEDIATE` | Noticeable issues | Small potholes, uneven patches |
| `BAD` | Poor condition | Many potholes, rough ride |
| `VERY_BAD` | Very poor condition | Large potholes, difficult to drive |
| `HORRIBLE` | Nearly undriveable | Extreme damage, very dangerous |
| `IMPASSABLE` | Cannot be used | Road is blocked or destroyed |
| `UNKNOWN` | No information | When OSM data is missing |

#### Visual Guide

```
EXCELLENT    ▓▓▓▓▓▓▓▓▓▓  Perfectly smooth
GOOD         ▓▓▓▓▓▓▓▓░░  Tiny bumps
INTERMEDIATE ▓▓▓▓▓░░░░░  Some rough patches
BAD          ▓▓░░░░░░░░  Many rough areas
VERY_BAD     ▓░░░░░░░░░  Mostly rough
HORRIBLE     ░░░░░░░░░░  Almost all bad
IMPASSABLE   ■■■■■■■■■■  Blocked/destroyed
```

#### Usage Example

```python
from domain.enums.road import Smoothness

# New highway
new_highway = Road(
    surface=Surface.ASPHALT,
    smoothness=Smoothness.EXCELLENT
)

# Old paved road
old_road = Road(
    surface=Surface.ASPHALT,
    smoothness=Smoothness.BAD  # Many potholes
)

# Dirt track in poor condition
rough_track = Road(
    surface=Surface.DIRT,
    smoothness=Smoothness.VERY_BAD
)
```

#### How Smoothness Affects Speed

```python
Smoothness.EXCELLENT     → factor = 1.0  (full speed)
Smoothness.GOOD          → factor = 0.9  (10% slower)
Smoothness.INTERMEDIATE  → factor = 0.8  (20% slower)
Smoothness.BAD           → factor = 0.6  (40% slower)
Smoothness.VERY_BAD      → factor = 0.3  (70% slower)
Smoothness.HORRIBLE      → factor = 0.1  (90% slower)
Smoothness.IMPASSABLE    → factor = 0.0  (cannot pass)
```

---

### 4. POICategory

Groups points of interest into broad categories.

#### Available Values

| Value | What It Includes | Examples |
|-------|------------------|----------|
| `TRANSPORT` | Travel-related services | Gas stations, parking, bus stations |
| `FOOD` | Places to eat and drink | Restaurants, cafes, fast food |
| `LODGING` | Places to sleep | Hotels, guest houses, motels |
| `SERVICES` | Useful services | Banks, ATMs, post offices |
| `HEALTH` | Medical services | Hospitals, pharmacies, clinics |
| `SHOPPING` | Places to buy things | Supermarkets, markets, convenience stores |
| `EDUCATION` | Schools and learning | Schools, universities, libraries |
| `GOVERNMENT` | Government services | Police stations, embassies, town halls |
| `UNKNOWN` | Unclassified | When category cannot be determined |

#### Usage Example

```python
from domain.enums.poi import POICategory

# Gas station
gas_station = POI(
    category=POICategory.TRANSPORT,
    subcategory="fuel",
    name="Total Gas Station"
)

# Restaurant
restaurant = POI(
    category=POICategory.FOOD,
    subcategory="restaurant",
    name="Chez Mariette"
)

# Hotel
hotel = POI(
    category=POICategory.LODGING,
    subcategory="hotel",
    name="Hotel Colbert"
)

# Pharmacy
pharmacy = POI(
    category=POICategory.HEALTH,
    subcategory="pharmacy",
    name="Pharmacie de l'Indépendance"
)
```

#### Why Categories Matter

Categories help with:

1. **Filtering** - "Show me all restaurants near this road"
2. **Icons** - Display different map symbols for different categories
3. **Planning** - "Find lodging every 200 km along this route"
4. **Statistics** - "Count all health facilities in each region"

#### Subcategories

Each category has many subcategories (stored as strings):

**TRANSPORT:**
- fuel, parking, bus_station, car_rental, charging_station

**FOOD:**
- restaurant, cafe, fast_food, bar, pub

**LODGING:**
- hotel, guest_house, motel, hostel, apartment

**SERVICES:**
- bank, atm, post_office, bureau_de_change

**HEALTH:**
- hospital, pharmacy, clinic, doctors, dentist

**SHOPPING:**
- supermarket, convenience, marketplace, mall

**EDUCATION:**
- school, university, college, kindergarten, library

**GOVERNMENT:**
- police, fire_station, embassy, townhall, courthouse

---

## How Enums Work Together

Here's a complete example showing how multiple enums describe a road:

```python
# Route Nationale 7 near Antsirabe
# - Primary road (major route)
# - Asphalt surface
# - Bad condition (many potholes from weather)
route = Road(
    id=123456,
    road_type=RoadType.PRIMARY,
    surface=Surface.ASPHALT,
    smoothness=Smoothness.BAD,
    name="Route Nationale 7"
)

# Calculate effective speed
penalty = RoadPenalty.from_road_attributes(
    surface=route.surface,      # ASPHALT → 1.0
    smoothness=route.smoothness, # BAD → 0.6
    is_rainy_season=False       # → 1.0
)
# Total penalty: 1.0 × 0.6 × 1.0 = 0.6

base_speed = 80  # km/h for PRIMARY road
effective_speed = base_speed * penalty.total_factor()
# = 80 × 0.6 = 48 km/h
```

## Working with Enums in Code

### Getting the String Value

```python
road_type = RoadType.PRIMARY
print(road_type.value)  # "primary"

surface = Surface.ASPHALT
print(surface.value)  # "asphalt"
```

### Creating from String

```python
# From OpenStreetMap data
osm_highway = "primary"
road_type = RoadType(osm_highway)  # RoadType.PRIMARY

osm_surface = "asphalt"
surface = Surface(osm_surface)  # Surface.ASPHALT
```

### Comparing Enums

```python
road_type = RoadType.PRIMARY

if road_type == RoadType.PRIMARY:
    print("This is a primary road")

if road_type in [RoadType.PRIMARY, RoadType.SECONDARY]:
    print("This is a major road")
```

### Listing All Values

```python
# Get all possible road types
all_types = list(RoadType)
for road_type in all_types:
    print(road_type.value)

# Output:
# motorway
# trunk
# primary
# secondary
# ...
```

## Summary

Enums provide controlled vocabularies for:

- **RoadType** - Classification by importance (motorway, primary, residential, etc.)
- **Surface** - Road material (asphalt, gravel, dirt, etc.)
- **Smoothness** - Physical condition (excellent, good, bad, etc.)
- **POICategory** - Type of place (transport, food, lodging, etc.)

Benefits:
- ✅ Prevent typos and invalid values
- ✅ Clear documentation of allowed values
- ✅ Better IDE support (autocomplete)
- ✅ Type safety (catches errors before runtime)
- ✅ Consistent data throughout the application
