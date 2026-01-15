"""PBF file reader for OSM data.

This reader extracts raw OSM data (ways, nodes, relations) without transformation.
Domain transformation is handled by the application layer (OSMExtractor).
"""

from collections.abc import Iterator
from pathlib import Path

from infrastructure.osm.types import RawWay, RawNode, RawRelation
from infrastructure.osm.handlers import (
    NodeCollector,
    WayHandler,
    NodeHandler,
    RelationHandler,
    WayCollector,
)
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class PBFReader:
    """Read raw OSM data from PBF files.

    This reader only extracts raw data. Use OSMExtractor from the application
    layer to transform raw data into domain entities.

    Usage:
        reader = PBFReader(Path("madagascar.osm.pbf"))

        # Get raw ways
        for raw_way in reader.read_raw_ways():
            # raw_way.osm_id, raw_way.tags, raw_way.coords
            ...
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize reader with PBF file path.

        Args:
            file_path: Path to .osm.pbf file
        """
        self.file_path = file_path
        if not file_path.exists():
            raise FileNotFoundError(f"PBF file not found: {file_path}")

        self._nodes: dict[int, tuple[float, float]] | None = None
        self._ways: dict[int, list[tuple[float, float]]] | None = None

    def _collect_nodes(self) -> dict[int, tuple[float, float]]:
        """First pass: collect all node coordinates."""
        if self._nodes is not None:
            return self._nodes

        logger.info("Collecting node coordinates", file=str(self.file_path))
        collector = NodeCollector()
        collector.apply_file(str(self.file_path), locations=True)
        self._nodes = collector.nodes
        logger.info("Collected nodes", count=len(self._nodes))
        return self._nodes

    def _collect_ways(self) -> dict[int, list[tuple[float, float]]]:
        """Collect way geometries for relation processing."""
        if self._ways is not None:
            return self._ways

        nodes = self._collect_nodes()
        logger.info("Collecting way geometries")
        collector = WayCollector(nodes)
        collector.apply_file(str(self.file_path))
        self._ways = collector.ways
        logger.info("Collected ways", count=len(self._ways))
        return self._ways

    def read_raw_ways(self) -> Iterator[RawWay]:
        """Stream raw ways from PBF file.

        Yields:
            RawWay objects with osm_id, tags, and coords
        """
        nodes = self._collect_nodes()
        ways: list[RawWay] = []

        def collect(raw: RawWay) -> None:
            ways.append(raw)

        logger.info("Extracting raw ways")
        handler = WayHandler(nodes, collect)
        handler.apply_file(str(self.file_path))
        logger.info("Extracted raw ways", count=len(ways))

        yield from ways

    def read_raw_nodes(self) -> Iterator[RawNode]:
        """Stream raw nodes (with tags) from PBF file.

        Yields:
            RawNode objects with osm_id, tags, lon, lat
        """
        nodes: list[RawNode] = []

        def collect(raw: RawNode) -> None:
            nodes.append(raw)

        logger.info("Extracting raw nodes")
        handler = NodeHandler(collect)
        handler.apply_file(str(self.file_path), locations=True)
        logger.info("Extracted raw nodes", count=len(nodes))

        yield from nodes

    def read_raw_relations(self) -> Iterator[RawRelation]:
        """Stream raw relations from PBF file.

        Yields:
            RawRelation objects with osm_id, tags, and coords
        """
        ways = self._collect_ways()
        relations: list[RawRelation] = []

        def collect(raw: RawRelation) -> None:
            relations.append(raw)

        logger.info("Extracting raw relations")
        handler = RelationHandler(ways, collect)
        handler.apply_file(str(self.file_path))
        logger.info("Extracted raw relations", count=len(relations))

        yield from relations
