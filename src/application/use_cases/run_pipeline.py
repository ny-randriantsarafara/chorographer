"""Run pipeline use case - ETL orchestration."""

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from time import perf_counter
from typing import Literal, TypeVar

from application.ports.extractor import DataExtractor
from application.ports.repository import GeoRepository
from application.services.async_pipeline import AsyncBatcher
from domain import Road
from domain.services import split_roads_into_segments
from infrastructure.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

EntityType = Literal["roads", "pois", "zones", "segments"]


@dataclass
class PipelineResult:
    """Result of running the ETL pipeline."""

    roads_count: int
    pois_count: int
    zones_count: int
    segments_count: int
    duration_seconds: float


class RunPipelineUseCase:
    """Run the ETL pipeline: extract from source -> load to repository.

    Supports two execution modes:
    - Sequential (default=False): Processes entities one type at a time
    - Parallel (default=True): Uses producer-consumer pattern and asyncio.gather
      for concurrent extraction and loading

    Usage:
        extractor = OSMExtractor(reader)  # implements DataExtractor
        repository = PostgresWriter(pool)  # implements GeoRepository

        # Parallel mode (default)
        pipeline = RunPipelineUseCase(extractor, repository)
        result = await pipeline.execute()

        # Sequential mode (fallback)
        pipeline = RunPipelineUseCase(extractor, repository, enable_parallel=False)
        result = await pipeline.execute()

        print(f"Loaded {result.roads_count} roads in {result.duration_seconds}s")
    """

    def __init__(
        self,
        extractor: DataExtractor,
        repository: GeoRepository,
        enable_parallel: bool = True,
        batch_size: int = 1000,
        queue_depth: int = 10,
    ) -> None:
        """Initialize the pipeline use case.

        Args:
            extractor: Data extractor port implementation
            repository: Geo repository port implementation
            enable_parallel: Enable parallel processing (default True)
            batch_size: Batch size for parallel processing
            queue_depth: Max batches to buffer in queue
        """
        self.extractor = extractor
        self.repository = repository
        self.enable_parallel = enable_parallel
        self.batch_size = batch_size
        self.queue_depth = queue_depth

    async def _process_with_queue(
        self,
        iterator: Iterator[T],
        save_batch_fn: Callable[[list[T]], Awaitable[int]],
    ) -> int:
        """Process entities using producer-consumer pattern.

        Args:
            iterator: Sync iterator yielding entities
            save_batch_fn: Async function to save a batch

        Returns:
            Total entities processed
        """
        batcher: AsyncBatcher[T] = AsyncBatcher(
            iterator,
            batch_size=self.batch_size,
            max_queue_size=self.queue_depth,
        )
        return await batcher.run(save_batch_fn)

    async def execute(
        self,
        entity_types: set[EntityType] | None = None,
    ) -> PipelineResult:
        """Run the pipeline for specified entity types.

        Args:
            entity_types: Set of entity types to process.
                         None means all types {"roads", "pois", "zones", "segments"}.

        Returns:
            PipelineResult with counts and duration.
        """
        types = entity_types or {"pois", "zones"}

        if self.enable_parallel:
            try:
                return await self._execute_parallel(types)
            except Exception as e:
                logger.warning(
                    "Parallel execution failed, falling back to sequential",
                    error=str(e),
                )
                return await self._execute_sequential(types)

        return await self._execute_sequential(types)

    async def _execute_sequential(
        self,
        types: set[EntityType],
    ) -> PipelineResult:
        """Sequential execution mode (original behavior)."""
        start = perf_counter()

        roads_count = 0
        pois_count = 0
        zones_count = 0
        segments_count = 0
        roads: list[Road] | None = None

        if "segments" in types:
            logger.info("Processing roads")
            roads = list(self.extractor.extract_roads())
            if "roads" in types:
                roads_count = await self.repository.save_roads(roads)
                logger.info("Roads processed", count=roads_count)
        elif "roads" in types:
            logger.info("Processing roads")
            roads_count = await self.repository.save_roads(
                self.extractor.extract_roads()
            )
            logger.info("Roads processed", count=roads_count)

        if "segments" in types:
            logger.info("Processing segments")
            segments = split_roads_into_segments(roads or [])
            segments_count = await self.repository.save_segments(segments)
            logger.info("Segments processed", count=segments_count)

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
            segments_count=segments_count,
            duration_seconds=round(duration, 2),
        )

    async def _execute_parallel(
        self,
        types: set[EntityType],
    ) -> PipelineResult:
        """Parallel execution mode using producer-consumer pattern.

        Processes entity types concurrently where possible:
        - POIs and Zones can run in parallel (independent extractors)
        - Roads must complete before segments (dependency)
        """
        start = perf_counter()
        logger.info("Running pipeline in parallel mode")

        roads_count = 0
        pois_count = 0
        zones_count = 0
        segments_count = 0

        # Determine what we need to process
        need_roads = "roads" in types or "segments" in types
        need_pois = "pois" in types
        need_zones = "zones" in types
        need_segments = "segments" in types

        # Phase 1: Process roads first if needed (segments depend on roads)
        roads: list[Road] = []
        if need_roads:
            logger.info("Processing roads (parallel mode)")
            # Collect roads for potential segment processing
            if need_segments:
                roads = list(self.extractor.extract_roads())
                if "roads" in types:
                    roads_count = await self._process_with_queue(
                        iter(roads),
                        self.repository.save_roads_batch,
                    )
                    logger.info("Roads processed", count=roads_count)
            else:
                roads_count = await self._process_with_queue(
                    self.extractor.extract_roads(),
                    self.repository.save_roads_batch,
                )
                logger.info("Roads processed", count=roads_count)

        # Phase 2: Process segments, POIs, and zones in parallel
        parallel_tasks: list[asyncio.Task[int]] = []
        task_names: list[str] = []

        if need_segments and roads:
            logger.info("Processing segments (parallel mode)")
            segments = split_roads_into_segments(roads)
            task = asyncio.create_task(
                self._process_with_queue(
                    iter(segments),
                    self.repository.save_segments_batch,
                )
            )
            parallel_tasks.append(task)
            task_names.append("segments")

        if need_pois:
            logger.info("Processing POIs (parallel mode)")
            task = asyncio.create_task(
                self._process_with_queue(
                    self.extractor.extract_pois(),
                    self.repository.save_pois_batch,
                )
            )
            parallel_tasks.append(task)
            task_names.append("pois")

        if need_zones:
            logger.info("Processing zones (parallel mode)")
            task = asyncio.create_task(
                self._process_with_queue(
                    self.extractor.extract_zones(),
                    self.repository.save_zones_batch,
                )
            )
            parallel_tasks.append(task)
            task_names.append("zones")

        # Wait for all parallel tasks to complete
        if parallel_tasks:
            results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

            for name, result in zip(task_names, results, strict=True):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to process {name}", error=str(result))
                    raise result

                if name == "segments":
                    segments_count = result
                    logger.info("Segments processed", count=segments_count)
                elif name == "pois":
                    pois_count = result
                    logger.info("POIs processed", count=pois_count)
                elif name == "zones":
                    zones_count = result
                    logger.info("Zones processed", count=zones_count)

        duration = perf_counter() - start

        return PipelineResult(
            roads_count=roads_count,
            pois_count=pois_count,
            zones_count=zones_count,
            segments_count=segments_count,
            duration_seconds=round(duration, 2),
        )
