# Domain Value Objects

## What are Value Objects?

Value Objects are simple pieces of information that describe properties of entities. Unlike entities, they don't have a unique identity. What matters is their value, not who they are.

Think of it this way:
- A **person** is an entity (has an ID, can change over time)
- A **birthday** is a value object (just a date, doesn't change, no ID needed)

## Key Characteristics

1. **Immutable** - Once created, they cannot be changed
2. **No Identity** - Two value objects with the same values are considered identical
3. **Self-validating** - They check that their values make sense when created

## The Four Value Objects

### 1. Coordinates

The simplest value object - represents a location on Earth using latitude and longitude.

#### What It Contains

```python
Coordinates(lat: float, lon: float)
```

- **lat** (latitude): Number between -90 and +90
  - Negative = South, Positive = North
  - Madagascar is around -18 to -25 (south of the equator)
  
- **lon** (longitude): Number between -180 and +180
  - Negative = West, Positive = East
  - Madagascar is around +43 to +50 (east of the prime meridian)

#### Why It's Immutable

Once you create coordinates for a location, they don't change. If you need different coordinates, you create a new Coordinates object.

#### Example Usage

```python
# Antananarivo city center
tana_center = Coordinates(lat=-18.8792, lon=47.5079)

# You can read the values
print(f"Latitude: {tana_center.lat}")
print(f"Longitude: {tana_center.lon}")

# But you cannot change them (immutable!)
# tana_center.lat = -19.0  # This would cause an error

# To get new coordinates, create a new object
another_location = Coordinates(lat=-19.0, lon=47.5)
```

#### Common Operations

```python
# Check if two locations are the same
coord1 = Coordinates(lat=-18.8792, lon=47.5079)
coord2 = Coordinates(lat=-18.8792, lon=47.5079)
coord3 = Coordinates(lat=-19.0, lon=47.5)

coord1 == coord2  # True (same values)
coord1 == coord3  # False (different values)

# Calculate distance between two points
distance = coord1.distance_to(coord2)  # Returns meters
```

---

### 2. Address

An Address represents a street address, built from OpenStreetMap's address tags.

#### What It Contains

| Field | What It Means | Example |
|-------|---------------|---------|
| `street` | Street name | "Avenue de l'Indépendance" |
| `housenumber` | Building number | "25" |
| `postcode` | Postal code | "101" |
| `city` | City or town name | "Antananarivo" |
| `district` | District name | "Antananarivo-Renivohitra" |
| `region` | Region name | "Analamanga" |
| `country` | Country name | "Madagascar" |

All fields are optional because not all places have complete addresses.

#### How It's Created

OpenStreetMap uses tags like `addr:street`, `addr:housenumber`, etc. We collect these and create an Address object.

#### Example Usage

```python
# Complete address
address = Address(
    street="Avenue de l'Indépendance",
    housenumber="25",
    city="Antananarivo",
    district="Antananarivo-Renivohitra",
    region="Analamanga",
    postcode="101",
    country="Madagascar"
)

# Partial address (only what's available)
simple_address = Address(
    street="Route Nationale 7",
    city="Antsirabe"
)

# Format for display
print(address.formatted())
# Output: "25 Avenue de l'Indépendance, Antananarivo, Analamanga, Madagascar"
```

#### Why Addresses are Value Objects

Two POIs with the same street address are at the same location, even if they're different businesses. The address itself has no identity - it's just information.

---

### 3. RoadPenalty

RoadPenalty represents how road conditions slow down travel. It's a multiplier applied to the base speed.

#### What It Contains

| Field | Range | What It Means |
|-------|-------|---------------|
| `surface_factor` | 0.0 to 1.0 | How the road surface affects speed |
| `smoothness_factor` | 0.0 to 1.0 | How the road condition affects speed |
| `rainy_season_factor` | 0.0 to 1.0 | How weather affects speed |

All values default to 1.0 (no penalty).

#### Surface Factor Values

| Surface Type | Factor | Meaning |
|--------------|--------|---------|
| Asphalt/Paved | 1.0 | Normal speed |
| Concrete | 0.95 | Nearly normal |
| Gravel | 0.7 | 30% slower |
| Dirt | 0.4 | 60% slower |
| Sand | 0.3 | 70% slower |

#### Smoothness Factor Values

| Smoothness | Factor | Meaning |
|------------|--------|---------|
| Excellent | 1.0 | Perfect condition |
| Good | 0.9 | Slightly slower |
| Intermediate | 0.8 | Noticeable bumps |
| Bad | 0.6 | Very rough |
| Very Bad | 0.3 | Extremely slow |
| Horrible | 0.1 | Nearly impassable |

#### Rainy Season Factor

In Madagascar, the rainy season (November to April) makes dirt and gravel roads much worse:
- **Paved roads**: 1.0 (no change)
- **Gravel roads**: 0.8 (20% slower)
- **Dirt roads**: 0.6 (40% slower)

#### How to Calculate Effective Speed

```python
effective_speed = base_speed × surface_factor × smoothness_factor × rainy_season_factor
```

#### Example Usage

```python
# Good asphalt road - no penalty
good_road = RoadPenalty(
    surface_factor=1.0,
    smoothness_factor=1.0,
    rainy_season_factor=1.0
)
base_speed = 80  # km/h
effective = base_speed * good_road.total_factor()
# effective = 80 km/h

# Dirt road in bad condition during rainy season
bad_dirt = RoadPenalty(
    surface_factor=0.4,   # Dirt
    smoothness_factor=0.6,  # Bad
    rainy_season_factor=0.6  # Rainy
)
base_speed = 60  # km/h
effective = base_speed * bad_dirt.total_factor()
# effective = 60 × 0.4 × 0.6 × 0.6 = 8.64 km/h
# Very slow!

# Create from road attributes
penalty = RoadPenalty.from_road_attributes(
    surface=Surface.GRAVEL,
    smoothness=Smoothness.INTERMEDIATE,
    is_rainy_season=True
)
```

#### Why Penalties are Important

Real travel time depends on road conditions. A 100 km trip on excellent asphalt might take 1 hour, but the same distance on poor dirt roads in the rain could take 6+ hours.

---

### 4. OperatingHours

OperatingHours represents when a business is open, parsed from OpenStreetMap's `opening_hours` tag.

#### What It Contains

The actual storage format can vary, but it represents business hours for each day of the week.

#### Common Formats

```
Mo-Fr 08:00-18:00              → Monday to Friday, 8 AM to 6 PM
Sa 08:00-12:00                 → Saturday, 8 AM to noon
Mo-Fr 09:00-12:00,14:00-18:00 → Split shift (lunch break)
24/7                           → Always open
```

#### Example Usage

```python
# Simple hours
hours = OperatingHours("Mo-Fr 08:00-18:00")

# Check if open now
if hours.is_open_now():
    print("The place is currently open")

# Check if open at specific time
from datetime import datetime
specific_time = datetime(2026, 1, 15, 10, 30)  # Wednesday 10:30 AM
if hours.is_open_at(specific_time):
    print("Open at that time")

# Get next opening time
next_open = hours.next_opening_time()
print(f"Opens next at: {next_open}")
```

#### Why It's a Value Object

Opening hours are just information. Two businesses with the same hours aren't the same business - but the hours themselves are just data with no identity.

#### Common Use Cases

1. **Filter POIs** - Show only gas stations that are currently open
2. **Trip Planning** - Make sure you arrive when the hotel is staffed
3. **Warnings** - Alert if you'll arrive at a restaurant after closing time

---

## Value Object Principles

### 1. Immutability

```python
# Once created, you cannot change them
coords = Coordinates(lat=-18.8792, lon=47.5079)
# coords.lat = -19.0  # ERROR! Cannot modify

# To get different coordinates, create a new object
new_coords = Coordinates(lat=-19.0, lon=47.5)
```

### 2. Equality by Value

```python
# Two objects with same values are considered equal
addr1 = Address(street="Avenue de l'Indépendance", city="Antananarivo")
addr2 = Address(street="Avenue de l'Indépendance", city="Antananarivo")
addr3 = Address(street="Route Nationale 7", city="Antsirabe")

addr1 == addr2  # True (same values)
addr1 == addr3  # False (different values)
```

### 3. Self-Validation

```python
# Value objects validate their data
coords = Coordinates(lat=-18.8792, lon=47.5079)  # OK

# This would raise an error:
# invalid = Coordinates(lat=200, lon=47.5)  # Latitude must be -90 to +90

# This would also raise an error:
# penalty = RoadPenalty(surface_factor=1.5)  # Cannot be > 1.0
```

## Summary

Value Objects represent simple, immutable pieces of information:

- **Coordinates** - A location on Earth
- **Address** - A street address
- **RoadPenalty** - Speed reduction factors
- **OperatingHours** - Business hours

They are:
- **Immutable** - Can't be changed after creation
- **Valuе-based** - Identity is determined by their values
- **Self-validating** - Check their own correctness
- **Reusable** - Can be shared across multiple entities

They make the code safer and easier to reason about because they can't be accidentally modified.
