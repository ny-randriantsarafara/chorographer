# Ostrakon Architecture

## Overview

Ostrakon follows a **Hexagonal Architecture** (also known as Ports & Adapters) organized into three layers:

- **Domain** - Core business logic, pure Python, no external dependencies
- **Application** - Use cases that orchestrate domain logic
- **Infrastructure** - External system implementations (OSM, PostgreSQL, config, logging)

## Directory Structure

```
src/
├── domain/                    # Core business logic (innermost layer)
│   ├── entities/              # Core data structures
│   │   ├── road.py            # Road with geometry, type, surface, smoothness
│   │   ├── poi.py             # Point of Interest (fuel, hotel, shop, etc.)
│   │   ├── zone.py            # Administrative boundary (region, district)
│   │   └── segment.py         # Road segment for routing graph
│   ├── value_objects/         # Immutable domain values
│   │   ├── coordinates.py     # Lat/Lon pair
│   │   ├── penalty.py         # RoadPenalty (surface, smoothness, seasonal)
│   │   └── operating_hours.py # Business hours parsing
│   └── exceptions/            # Domain errors
│       ├── extraction.py      # ExtractionError
│       ├── transformation.py  # TransformationError
│       └── validation.py      # ValidationError
│
├── application/               # Use cases (middle layer)
│   ├── extract_osm.py         # Extract data from OSM file
│   ├── transform_data.py      # Transform OSM → domain entities
│   ├── load_postgres.py       # Load entities into PostgreSQL
│   └── run_pipeline.py        # Orchestrate full ETL
│
├── infrastructure/            # External systems (outermost layer)
│   ├── osm/                   # OSM file reader
│   │   └── pbf_reader.py      # Osmium-based .pbf parser
│   ├── postgres/              # Database writer
│   │   └── writer.py          # Psycopg-based writer
│   ├── config/                # Configuration
│   │   └── settings.py        # Pydantic settings
│   └── logging/               # Structured logging
│       └── setup.py           # Structlog configuration
│
└── main.py                    # Entry point
```

## Layer Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INFRASTRUCTURE                                  │
│  ┌─────────────────┐                                  ┌──────────────────┐  │
│  │   OSM Reader    │                                  │  PostgreSQL      │  │
│  │   (osmium)      │                                  │  Writer          │  │
│  │                 │                                  │  (psycopg)       │  │
│  │  ┌───────────┐  │                                  │  ┌────────────┐  │  │
│  │  │ .pbf file │  │                                  │  │ indri DB   │  │  │
│  │  └───────────┘  │                                  │  └────────────┘  │  │
│  └────────┬────────┘                                  └────────▲─────────┘  │
│           │                                                    │            │
│           │ reads                                        writes│            │
│           ▼                                                    │            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                           APPLICATION                                   │ │
│  │  ┌──────────────┐    ┌────────────────┐    ┌─────────────────┐         │ │
│  │  │ ExtractOSM   │───▶│ TransformData  │───▶│ LoadToPostgres  │         │ │
│  │  │ UseCase      │    │ UseCase        │    │ UseCase         │         │ │
│  │  └──────────────┘    └───────┬────────┘    └─────────────────┘         │ │
│  │                              │                                          │ │
│  │                              │ uses                                     │ │
│  │                              ▼                                          │ │
│  │  ┌────────────────────────────────────────────────────────────────────┐│ │
│  │  │                          DOMAIN                                     ││ │
│  │  │  ┌────────┐  ┌────────┐  ┌────────────┐  ┌─────────┐               ││ │
│  │  │  │ Road   │  │ POI    │  │ Zone       │  │ Segment │  (entities)   ││ │
│  │  │  └────────┘  └────────┘  └────────────┘  └─────────┘               ││ │
│  │  │                                                                     ││ │
│  │  │  ┌──────────────┐  ┌─────────┐  ┌────────────────┐                 ││ │
│  │  │  │ Coordinates  │  │ Penalty │  │ OperatingHours │ (value objects) ││ │
│  │  │  └──────────────┘  └─────────┘  └────────────────┘                 ││ │
│  │  └────────────────────────────────────────────────────────────────────┘│ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                                   │
│  │ Config          │  │ Logging         │  (cross-cutting)                  │
│  │ (pydantic)      │  │ (structlog)     │                                   │
│  └─────────────────┘  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐      ┌──────────┐
│  .pbf    │      │  Extract  │      │ Transform │      │   Load    │      │ PostgreSQL│
│  file    │─────▶│  UseCase  │─────▶│  UseCase  │─────▶│  UseCase  │─────▶│  (indri)  │
│(Madagascar)     │           │      │           │      │           │      │           │
└──────────┘      └───────────┘      └───────────┘      └───────────┘      └──────────┘
                        │                  │                  │
                        │                  │                  │
                        ▼                  ▼                  ▼
                  ┌───────────┐      ┌───────────┐      ┌───────────┐
                  │ OSMReader │      │  Domain   │      │ PGWriter  │
                  │ (infra)   │      │ Entities  │      │ (infra)   │
                  └───────────┘      └───────────┘      └───────────┘
```

## Dependency Rules

1. **Domain** has NO external dependencies - pure Python only
2. **Application** depends on Domain, defines interfaces for Infrastructure
3. **Infrastructure** depends on Application and Domain, implements interfaces

```
Infrastructure ──▶ Application ──▶ Domain
     │                  │              │
     │                  │              └── No dependencies
     │                  └── Depends on Domain only
     └── Depends on Application and Domain
```

## Key Principles

- **Dependency Inversion**: High-level modules (Application) define interfaces, low-level modules (Infrastructure) implement them
- **Single Responsibility**: Each layer has one reason to change
- **Testability**: Domain and Application can be tested without Infrastructure
- **Flexibility**: Infrastructure implementations can be swapped without affecting business logic

---

## Domain Model

### Entities

#### Road
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `osm_id` | int | OSM | Unique identifier for versioning |
| `geometry` | list[Coordinates] | OSM | LineString coordinates |
| `road_type` | RoadType | OSM `highway` | primary, secondary, tertiary, residential, track |
| `surface` | Surface | OSM `surface` | asphalt, gravel, dirt, sand |
| `smoothness` | Smoothness | OSM `smoothness` | excellent, good, intermediate, bad, very_bad |
| `name` | str \| None | OSM `name` | Road name |
| `lanes` | int | OSM `lanes` | Number of lanes (default: 2) |
| `oneway` | bool | OSM `oneway` | One-way restriction |
| `max_speed` | int \| None | OSM `maxspeed` | Speed limit in km/h |

#### POI (Point of Interest)
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `osm_id` | int | OSM | Unique identifier |
| `coordinates` | Coordinates | OSM | Location |
| `category` | POICategory | OSM | transport, food, lodging, services, health |
| `subcategory` | str | OSM `amenity`/`shop` | fuel, restaurant, hotel, pharmacy, etc. |
| `name` | str \| None | OSM `name` | Business name |
| `address` | Address \| None | OSM `addr:*` | Street address if available |
| `phone` | str \| None | OSM/scraped | Contact phone |
| `opening_hours` | OperatingHours \| None | OSM/scraped | Business hours |
| `price_range` | int \| None | scraped | 1-4 scale |

#### Zone (Administrative Boundary)
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `osm_id` | int | OSM | Unique identifier |
| `geometry` | list[Coordinates] | OSM | Polygon boundary |
| `admin_level` | int | OSM | 4=region, 6=district, 8=commune |
| `name` | str | OSM `name` | Zone name |
| `malagasy_name` | str \| None | OSM `name:mg` | Malagasy name |
| `iso_code` | str \| None | OSM `ISO3166-2` | ISO code (e.g., MG-A) |

#### Segment (for routing graph)
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `id` | int | derived | Unique segment ID |
| `road_id` | int | derived | Parent road OSM ID |
| `start` | Coordinates | derived | Start node |
| `end` | Coordinates | derived | End node |
| `length` | float | computed | Segment length in meters |
| `penalty` | RoadPenalty | computed | Speed multiplier |

### Value Objects

#### Coordinates
```
(lat: float, lon: float)
```

#### RoadPenalty
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `surface_factor` | float | 1.0 | asphalt=1.0, gravel=0.7, dirt=0.4, sand=0.3 |
| `smoothness_factor` | float | 1.0 | excellent=1.0, good=0.9, bad=0.6, very_bad=0.3 |
| `rainy_season_factor` | float | 1.0 | Multiplier during Nov-Apr (0.6 for dirt roads) |

**Effective speed** = `base_speed × surface_factor × smoothness_factor × rainy_season_factor`

#### OperatingHours
Parsed from OSM `opening_hours` tag (e.g., `Mo-Fr 08:00-18:00; Sa 08:00-12:00`)

### Enums

```python
class RoadType(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    RESIDENTIAL = "residential"
    TRACK = "track"
    UNCLASSIFIED = "unclassified"

class Surface(Enum):
    ASPHALT = "asphalt"
    PAVED = "paved"
    GRAVEL = "gravel"
    DIRT = "dirt"
    SAND = "sand"
    UNPAVED = "unpaved"

class Smoothness(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    INTERMEDIATE = "intermediate"
    BAD = "bad"
    VERY_BAD = "very_bad"
    HORRIBLE = "horrible"

class POICategory(Enum):
    TRANSPORT = "transport"    # fuel, parking, bus_station
    FOOD = "food"              # restaurant, cafe, fast_food
    LODGING = "lodging"        # hotel, guest_house, motel
    SERVICES = "services"      # bank, atm, post_office
    HEALTH = "health"          # hospital, pharmacy, clinic
    SHOPPING = "shopping"      # supermarket, convenience, market
```
