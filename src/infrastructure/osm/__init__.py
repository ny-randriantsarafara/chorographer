"""OSM infrastructure - OpenStreetMap data extraction.

Uses osmium library to parse .pbf files and transform OSM data into domain entities.
All OSM-specific knowledge (tag parsing, filtering) is encapsulated here.
"""

from infrastructure.osm.reader import PBFReader
from infrastructure.osm.extractor import OSMExtractor
from infrastructure.osm.types import RawWay, RawNode, RawRelation

__all__ = ["PBFReader", "OSMExtractor", "RawWay", "RawNode", "RawRelation"]
