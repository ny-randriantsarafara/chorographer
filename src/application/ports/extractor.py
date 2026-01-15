"""Data extractor port - Abstract interface for extracting domain entities."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from domain import Road, POI, Zone


class DataExtractor(ABC):
    """Port for extracting domain entities from any data source.

    Infrastructure adapters (OSM, GeoJSON, etc.) implement this interface
    to provide domain entities to application use cases.
    """

    @abstractmethod
    def extract_roads(self) -> Iterator[Road]:
        """Extract roads from the data source.

        Yields:
            Road domain entities
        """
        ...

    @abstractmethod
    def extract_pois(self) -> Iterator[POI]:
        """Extract points of interest from the data source.

        Yields:
            POI domain entities
        """
        ...

    @abstractmethod
    def extract_zones(self) -> Iterator[Zone]:
        """Extract administrative zones from the data source.

        Yields:
            Zone domain entities
        """
        ...
