"""Zone hierarchy computation using spatial containment."""

import logging
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


async def compute_zone_hierarchy(pool: AsyncConnectionPool) -> None:
    """Compute parent_zone_id for all zones using spatial containment.
    
    For each zone, finds the smallest zone at the next level up (level - 1)
    that contains its centroid. Processes bottom-up from level 4 to level 1.
    
    Args:
        pool: Database connection pool
    """
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # Process each level from 4 (fokontany) to 2 (district)
            # Level 1 (region) has no parent
            for level in range(4, 1, -1):
                await cur.execute(
                    """
                    UPDATE zones AS child
                    SET parent_zone_id = (
                        SELECT parent.id
                        FROM zones AS parent
                        WHERE parent.level = %s
                          AND ST_Contains(parent.geometry, ST_Centroid(child.geometry))
                        ORDER BY ST_Area(parent.geometry) ASC
                        LIMIT 1
                    )
                    WHERE child.level = %s
                    """,
                    (level - 1, level),
                )
                
                rows_updated = cur.rowcount
                logger.info(
                    f"Updated parent_zone_id for {rows_updated} zones at level {level}"
                )
            
            await conn.commit()
