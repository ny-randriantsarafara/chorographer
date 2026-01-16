"""Application entry point."""

import asyncio
from dataclasses import asdict

from application import RunPipelineUseCase
from infrastructure.config import get_settings
from infrastructure.logging import setup_logging, get_logger
from infrastructure.osm import PBFReader, OSMExtractor
from infrastructure.postgres import create_pool, PostgresWriter

logger = get_logger(__name__)


async def run() -> None:
    """Run the Chorographer ETL pipeline."""
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
        result = await pipeline.execute()

        logger.info("Pipeline complete", **asdict(result))


def main() -> None:
    """Entry point."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
