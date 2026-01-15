"""Run pipeline use case - ETL orchestration."""

from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from application.ports.extractor import DataExtractor
from application.ports.repository import GeoRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)

EntityType = Literal["roads", "pois", "zones"]


@dataclass
class PipelineResult:
    """Result of running the ETL pipeline."""

    roads_count: int
    pois_count: int
    zones_count: int
    duration_seconds: float


class RunPipelineUseCase:
    """Run the ETL pipeline: extract from source -> load to repository.

    Uses streaming: extracts and loads each entity type sequentially,
    passing iterators directly to the repository (memory efficient).

    Usage:
        extractor = OSMExtractor(reader)  # implements DataExtractor
        repository = PostgresWriter(pool)  # implements GeoRepository

        pipeline = RunPipelineUseCase(extractor, repository)
        result = await pipeline.execute()

        print(f"Loaded {result.roads_count} roads in {result.duration_seconds}s")
    """

    def __init__(
        self,
        extractor: DataExtractor,
        repository: GeoRepository,
    ) -> None:
        """Initialize the pipeline use case.

        Args:
            extractor: Data extractor port implementation
            repository: Geo repository port implementation
        """
        self.extractor = extractor
        self.repository = repository

    async def execute(
        self,
        entity_types: set[EntityType] | None = None,
    ) -> PipelineResult:
        """Run the pipeline for specified entity types.

        Args:
            entity_types: Set of entity types to process.
                         None means all types {"roads", "pois", "zones"}.

        Returns:
            PipelineResult with counts and duration.
        """
        start = perf_counter()
        types = entity_types or {"roads", "pois", "zones"}

        roads_count = 0
        pois_count = 0
        zones_count = 0

        if "roads" in types:
            logger.info("Processing roads")
            roads_count = await self.repository.save_roads(
                self.extractor.extract_roads()
            )
            logger.info("Roads processed", count=roads_count)

        if "pois" in types:
            logger.info("Processing POIs")
            pois_count = await self.repository.save_pois(
                self.extractor.extract_pois()
            )
            logger.info("POIs processed", count=pois_count)

        if "zones" in types:
            logger.info("Processing zones")
            zones_count = await self.repository.save_zones(
                self.extractor.extract_zones()
            )
            logger.info("Zones processed", count=zones_count)

        duration = perf_counter() - start

        return PipelineResult(
            roads_count=roads_count,
            pois_count=pois_count,
            zones_count=zones_count,
            duration_seconds=round(duration, 2),
        )
