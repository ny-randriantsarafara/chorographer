"""Osmium handlers for parsing PBF files.

These handlers extract raw OSM data without any domain transformation.
Transformation is handled by the application layer.
"""

from collections.abc import Callable

import osmium
from osmium.osm import Way, Node, Relation

from infrastructure.osm.types import RawWay, RawNode, RawRelation


class NodeCollector(osmium.SimpleHandler):
    """First pass: collect node coordinates for building way geometries."""

    def __init__(self) -> None:
        super().__init__()
        self.nodes: dict[int, tuple[float, float]] = {}

    def node(self, n: Node) -> None:
        """Store node coordinates."""
        self.nodes[n.id] = (n.location.lon, n.location.lat)


class WayHandler(osmium.SimpleHandler):
    """Extract all ways as raw data."""

    def __init__(
        self,
        nodes: dict[int, tuple[float, float]],
        callback: Callable[[RawWay], None],
    ) -> None:
        super().__init__()
        self.nodes = nodes
        self.callback = callback

    def way(self, w: Way) -> None:
        """Process way and emit raw data."""
        tags = {tag.k: tag.v for tag in w.tags}

        # Build geometry from node references
        coords: list[tuple[float, float]] = []
        for node_ref in w.nodes:
            if node_ref.ref in self.nodes:
                coords.append(self.nodes[node_ref.ref])

        if len(coords) < 2:
            return

        raw = RawWay(osm_id=w.id, tags=tags, coords=coords)
        self.callback(raw)


class NodeHandler(osmium.SimpleHandler):
    """Extract nodes with tags as raw data."""

    def __init__(self, callback: Callable[[RawNode], None]) -> None:
        super().__init__()
        self.callback = callback

    def node(self, n: Node) -> None:
        """Process node and emit raw data if it has tags."""
        if not n.tags:
            return

        tags = {tag.k: tag.v for tag in n.tags}
        raw = RawNode(
            osm_id=n.id,
            tags=tags,
            lon=n.location.lon,
            lat=n.location.lat,
        )
        self.callback(raw)


class RelationHandler(osmium.SimpleHandler):
    """Extract relations as raw data."""

    def __init__(
        self,
        ways: dict[int, list[tuple[float, float]]],
        callback: Callable[[RawRelation], None],
    ) -> None:
        super().__init__()
        self.ways = ways
        self.callback = callback

    def relation(self, r: Relation) -> None:
        """Process relation and emit raw data."""
        tags = {tag.k: tag.v for tag in r.tags}

        # Build geometry from outer way members
        coords: list[tuple[float, float]] = []
        for member in r.members:
            if member.type == "w" and member.role in ("outer", ""):
                if member.ref in self.ways:
                    coords.extend(self.ways[member.ref])

        if len(coords) < 3:
            return

        raw = RawRelation(osm_id=r.id, tags=tags, coords=coords)
        self.callback(raw)


class WayCollector(osmium.SimpleHandler):
    """Collect way geometries for building relation polygons."""

    def __init__(self, nodes: dict[int, tuple[float, float]]) -> None:
        super().__init__()
        self.nodes = nodes
        self.ways: dict[int, list[tuple[float, float]]] = {}

    def way(self, w: Way) -> None:
        """Store way coordinates."""
        coords: list[tuple[float, float]] = []
        for node_ref in w.nodes:
            if node_ref.ref in self.nodes:
                coords.append(self.nodes[node_ref.ref])
        if coords:
            self.ways[w.id] = coords
