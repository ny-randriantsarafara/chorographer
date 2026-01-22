"""Data enrichment operations to run after initial ETL."""

import asyncio
import argparse

from application import ComputeZoneHierarchyUseCase
from infrastructure.config import get_settings
from infrastructure.logging import setup_logging, get_logger
from infrastructure.postgres import create_pool

logger = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run data enrichment operations.")
    parser.add_argument(
        "--compute-hierarchy",
        action="store_true",
        help="Compute zone parent_zone_id relationships via spatial containment",
    )
    return parser.parse_args()


async def run(compute_hierarchy: bool) -> None:
    """Run enrichment operations.
    
    Args:
        compute_hierarchy: Whether to compute zone hierarchy
    """
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)

    logger.info("Starting enrichment operations")

    async with create_pool(settings) as pool:
        if compute_hierarchy:
            hierarchy_use_case = ComputeZoneHierarchyUseCase(pool)
            await hierarchy_use_case.execute()

    logger.info("Enrichment operations complete")


def main() -> None:
    """Entry point."""
    args = _parse_args()
    
    if not args.compute_hierarchy:
        logger.warning("No enrichment operations specified. Use --compute-hierarchy")
        return
    
    asyncio.run(run(compute_hierarchy=args.compute_hierarchy))


if __name__ == "__main__":
    main()
