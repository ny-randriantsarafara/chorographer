"""Domain entities - Core data structures for Madagascar routing."""

from domain.entities.road import Road
from domain.entities.poi import POI
from domain.entities.zone import Zone
from domain.entities.segment import Segment

__all__ = [
    "Road",
    "POI",
    "Zone",
    "Segment",
]
