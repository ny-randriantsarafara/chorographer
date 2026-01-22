"""Compute zone hierarchy use case."""

from time import perf_counter

from infrastructure.logging import get_logger
from infrastructure.postgres.zone_hierarchy import compute_zone_hierarchy
from psycopg_pool import AsyncConnectionPool

logger = get_logger(__name__)


class ComputeZoneHierarchyUseCase:
    """Compute parent_zone_id for all zones based on spatial containment.
    
    This use case should be run after zones have been loaded into the database.
    It uses PostGIS spatial queries to determine which zone contains which,
    building the administrative hierarchy tree.
    
    Usage:
        async with create_pool(settings) as pool:
            use_case = ComputeZoneHierarchyUseCase(pool)
            relationships_count = await use_case.execute()
            print(f"Established {relationships_count} parent relationships")
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        """Initialize the use case.
        
        Args:
            pool: Database connection pool
        """
        self.pool = pool

    async def execute(self) -> int:
        """Execute zone hierarchy computation.
        
        Returns:
            Number of parent-child relationships established
        """
        logger.info("Computing zone hierarchy via spatial containment")
        start = perf_counter()
        
        count = await compute_zone_hierarchy(self.pool)
        
        duration = perf_counter() - start
        logger.info(
            "Zone hierarchy computed",
            relationships=count,
            duration_seconds=round(duration, 2),
        )
        
        return count
