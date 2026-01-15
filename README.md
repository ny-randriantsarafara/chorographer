# Chorographer

ETL pipeline for extracting OpenStreetMap (OSM) data from Madagascar and ingesting it into PostgreSQL (indri database).

## Architecture

This project follows **Hexagonal Architecture** (Domain / Application / Infrastructure):

```
src/
├── domain/           # Core business logic
│   ├── entities/     # Domain entities (Node, Way, Relation, etc.)
│   └── exceptions/   # Domain-specific exceptions
├── application/      # Use cases and orchestration
│   └── use_cases/    # ExtractOSM, TransformData, LoadToPostgres
└── infrastructure/   # External system implementations
    ├── osm/          # OSM file reader (osmium)
    ├── postgres/     # Database writer (psycopg)
    ├── config/       # Configuration (pydantic-settings)
    └── logging/      # Structured logging (structlog)
```

## Data Flow

```
OSM File (.pbf) → Infrastructure (Reader) → Application (Use Cases) → Infrastructure (Writer) → PostgreSQL (indri)
```

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the pipeline
chorographer --config config.yaml
```

## Configuration

Configure via environment variables or `config.yaml`:

- `OSM_FILE_PATH`: Path to the Madagascar OSM extract (.pbf)
- `POSTGRES_DSN`: PostgreSQL connection string for indri database

## License

MIT
