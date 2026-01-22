"""Application entry point."""

import argparse
import asyncio
from dataclasses import asdict

from application import RunPipelineUseCase
from infrastructure.config import get_settings
from infrastructure.logging import setup_logging, get_logger
from infrastructure.osm import PBFReader, OSMExtractor
from infrastructure.postgres import create_pool, PostgresWriter

logger = get_logger(__name__)

ENTITY_TYPES = ("roads", "pois", "zones", "segments")


def _parse_entity_types(raw_values: list[str] | None) -> set[str] | None:
    if not raw_values:
        return None

    types: set[str] = set()
    for raw in raw_values:
        for value in raw.split(","):
            normalized = value.strip().lower()
            if not normalized:
                continue
            if normalized not in ENTITY_TYPES:
                raise ValueError(
                    f"Invalid entity type '{value}'. "
                    f"Use one of: {', '.join(ENTITY_TYPES)}."
                )
            types.add(normalized)

    return types or None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Chorographer ETL pipeline.")
    parser.add_argument(
        "--entity-type",
        action="append",
        help=(
            "Entity type to process. Repeat or use commas, e.g. "
            "--entity-type roads --entity-type pois,zones."
        ),
    )
    return parser.parse_args()


async def run(entity_types: set[str] | None) -> None:
    """Run the Chorographer ETL pipeline.
    
    Args:
        entity_types: Entity types to extract (None = all)
    """
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)

    logger.info("Starting chorographer ETL pipeline")

    # Infrastructure adapters
    reader = PBFReader(settings.osm_file_path)
    extractor = OSMExtractor(reader)

    async with create_pool(settings) as pool:
        repository = PostgresWriter(pool, settings.batch_size)

        # Application use case
        pipeline = RunPipelineUseCase(
            extractor,
            repository,
            enable_parallel=settings.enable_parallel_pipeline,
            batch_size=settings.batch_size,
            queue_depth=settings.parallel_queue_depth,
        )
        result = await pipeline.execute(entity_types=entity_types)

        logger.info("Pipeline complete", **asdict(result))
        
        # Optionally compute zone hierarchy
        if compute_hierarchy:
            hierarchy_use_case = ComputeZoneHierarchyUseCase(pool)
            await hierarchy_use_case.execute()



def main() -> None:
    """Entry point."""
    args = _parse_args()
    try:
        entity_types = _parse_entity_types(args.entity_type)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    asyncio.run(run(entity_types