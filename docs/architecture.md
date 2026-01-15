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
│   ├── entities/              # Data structures
│   │   ├── node.py            # OSM Node
│   │   ├── way.py             # OSM Way
│   │   ├── relation.py        # OSM Relation
│   │   └── tag.py             # OSM Tag
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
│  │  │  │ Node   │  │ Way    │  │ Relation   │  │ Tag     │  (entities)   ││ │
│  │  │  └────────┘  └────────┘  └────────────┘  └─────────┘               ││ │
│  │  │                                                                     ││ │
│  │  │  ┌───────────────────┐  ┌─────────────────────┐                    ││ │
│  │  │  │ ExtractionError   │  │ TransformationError │  (exceptions)      ││ │
│  │  │  └───────────────────┘  └─────────────────────┘                    ││ │
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
