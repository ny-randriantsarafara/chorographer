"""Osmium handlers for parsing PBF files.

These handlers extract raw OSM data without any domain transformation.
Transformation is handled by the application layer.
"""

from collections.abc import Callable

import osmium
from osmium.osm import Node, Relation, Way

from infrastructure.osm.types import RawNode, RawRelation, RawWay


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


class CombinedHandler(osmium.SimpleHandler):
    """Extract ways, nodes, and relations in a single pass.

    This handler processes all entity types during one file scan,
    improving performance for parallel entity processing by avoiding
    multiple passes over the PBF file.

    Usage:
        nodes = node_collector.nodes  # Pre-collected node coordinates
        ways = way_collector.ways     # Pre-collected way geometries

        raw_ways, raw_nodes, raw_relations = [], [], []
        handler = CombinedHandler(
            nodes, ways,
            on_way=raw_ways.append,
            on_node=raw_nodes.append,
            on_relation=raw_relations.append,
        )
        handler.apply_file(str(file_path))
    """

    def __init__(
        self,
        node_coords: dict[int, tuple[float, float]],
        way_coords: dict[int, list[tuple[float, float]]],
        on_way: Callable[[RawWay], None],
        on_node: Callable[[RawNode], None],
        on_relation: Callable[[RawRelation], None],
    ) -> None:
        """Initialize combined handler.

        Args:
            node_coords: Pre-collected node coordinates (id -> (lon, lat))
            way_coords: Pre-collected way geometries (id -> [(lon, lat), ...])
            on_way: Callback for each extracted way
            on_node: Callback for each extracted node with tags
            on_relation: Callback for each extracted relation
        """
        super().__init__()
        self.node_coords = node_coords
        self.way_coords = way_coords
        self.on_way = on_way
        self.on_node = on_node
        self.on_relation = on_relation

    def way(self, w: Way) -> None:
        """Process way and emit raw data."""
        tags = {tag.k: tag.v for tag in w.tags}

        # Build geometry from node references
        coords: list[tuple[float, float]] = []
        for node_ref in w.nodes:
            if node_ref.ref in self.node_coords:
                coords.append(self.node_coords[node_ref.ref])

        if len(coords) < 2:
            return

        raw = RawWay(osm_id=w.id, tags=tags, coords=coords)
        self.on_way(raw)

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
        self.on_node(raw)

    def relation(self, r: Relation) -> None:
        """Process relation and emit raw data."""
        tags = {tag.k: tag.v for tag in r.tags}

        # Build geometry from outer way members
        coords: list[tuple[float, float]] = []
        for member in r.members:
            if member.type == "w" and member.role in ("outer", ""):
                if member.ref in self.way_coords:
                    coords.extend(self.way_coords[member.ref])

        if len(coords) < 3:
            return

        raw = RawRelation(osm_id=r.id, tags=tags, coords=coords)
        self.on_relation(raw)
