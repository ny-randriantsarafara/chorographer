"""Geo repository port - Abstract interface for persisting domain entities."""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from domain import Road, POI, Zone, Segment


class GeoRepository(ABC):
    """Port for persisting domain entities to any storage.

    Infrastructure adapters (PostgreSQL, file storage, etc.) implement this
    interface to store domain entities from application use cases.
    """

    @abstractmethod
    async def save_roads(self, roads: Iterable[Road]) -> int:
        """Save roads to the repository.

        Args:
            roads: Iterable of Road entities to save

        Returns:
            Number of roads saved
        """
        ...

    @abstractmethod
    async def save_pois(self, pois: Iterable[POI]) -> int:
        """Save points of interest to the repository.

        Args:
            pois: Iterable of POI entities to save

        Returns:
            Number of POIs saved
        """
        ...

    @abstractmethod
    async def save_zones(self, zones: Iterable[Zone]) -> int:
        """Save administrative zones to the repository.

        Args:
            zones: Iterable of Zone entities to save

        Returns:
            Number of zones saved
        """
        ...

    @abstractmethod
    async def save_segments(self, segments: Iterable[Segment]) -> int:
        """Save road segments to the repository.

        Args:
            segments: Iterable of Segment entities to save

        Returns:
            Number of segments saved
        """
        ...
