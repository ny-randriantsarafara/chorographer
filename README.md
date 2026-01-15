# Chorographer

ETL pipeline for extracting OpenStreetMap (OSM) data from Madagascar and ingesting it into PostgreSQL (lemurion database).

**Keywords:** OpenStreetMap, OSM, Madagascar, ETL, geospatial, PostGIS, PostgreSQL, hexagonal architecture, data pipeline

## Architecture

This project follows **Hexagonal Architecture** (Domain / Application / Infrastructure):

```
src/
├── domain/           # Core business logic
│   ├── entities/     # Domain entities (Road, POI, Zone, Segment)
│   ├── enums/        # Domain classification enums
│   ├── value_objects/ # Coordinates, Address, OperatingHours, RoadPenalty
│   └── exceptions/   # Domain-specific exceptions
├── application/      # Use cases and orchestration
│   ├── ports/        # DataExtractor, GeoRepository
│   └── use_cases/    # RunPipelineUseCase
└── infrastructure/   # External system implementations
    ├── osm/          # OSM file reader (osmium)
    ├── postgres/     # Database writer (psycopg)
    ├── config/       # Configuration (pydantic-settings)
    └── logging/      # Structured logging (structlog)
```

## Data Flow

```
OSM File (.pbf) → Infrastructure (Reader) → Application (Use Cases) → Infrastructure (Writer) → PostgreSQL (lemurion)
```

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"
```

## Usage

Run the pipeline from the source tree:

```bash
cd src
python -m main
```

Or from the repository root:

```bash
PYTHONPATH=src python -m main
```

## Configuration

Configure via environment variables or a local `.env` file:

- `OSM_FILE_PATH`: Path to the OSM extract (.pbf)
- `POSTGRES_HOST`: PostgreSQL host (default: `localhost`)
- `POSTGRES_PORT`: PostgreSQL port (default: `5432`)
- `POSTGRES_DB`: PostgreSQL database name (default: `lemurion`)
- `POSTGRES_USER`: PostgreSQL user (default: `postgres`)
- `POSTGRES_PASSWORD`: PostgreSQL password
- `BATCH_SIZE`: Insert batch size (default: `1000`)
- `LOG_LEVEL`: Log level (default: `INFO`)
- `LOG_FORMAT`: `console` or `json` (default: `console`)