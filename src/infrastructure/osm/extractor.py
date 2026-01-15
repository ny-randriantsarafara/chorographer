"""OSM data extraction service.

Orchestrates reading raw OSM data and transforming it into domain entities.
All OSM-specific knowledge (tag parsing, filtering) lives here in infrastructure.
"""

from collections.abc import Iterator

from application.ports.extractor import DataExtractor
from domain import Road, POI, Zone
from infrastructure.osm.reader import PBFReader
from infrastructure.osm.transformers import transform_road, transform_poi, transform_zone
from infrastructure.logging import get_logger

logger = get_logger(__name__)

# OSM highway types we consider as roads
ROAD_HIGHWAY_TYPES = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "residential",
    "living_street",
    "unclassified",
    "track",
    "path",
    "footway",
    "cycleway",
}

# OSM tags that identify POIs
POI_TAGS = {"amenity", "shop", "tourism"}


class OSMExtractor(DataExtractor):
    """Extracts and transforms OSM data into domain entities.

    All OSM-specific knowledge (tag parsing, filtering by highway type, etc.)
    is encapsulated here in the infrastructure layer.

    Usage:
        from infrastructure.osm import PBFReader, OSMExtractor

        reader = PBFReader(Path("madagascar.osm.pbf"))
        extractor = OSMExtractor(reader)

        for road in extractor.extract_roads():
            print(road.name, road.road_type)

        for poi in extractor.extract_pois():
            print(poi.name, poi.category)

        for zone in extractor.extract_zones():
            print(zone.name, zone.admin_level)
    """

    def __init__(self, reader: PBFReader) -> None:
        """Initialize extractor with a PBF reader.

        Args:
            reader: Infrastructure layer PBF reader for raw OSM data
        """
        self.reader = reader

    def extract_roads(self) -> Iterator[Road]:
        """Extract and transform roads from OSM data.

        Filters raw ways to only include highway types and transforms
        them into Road domain entities.

        Yields:
            Road domain entities
        """
        logger.info("Extracting roads from OSM data")
        count = 0

        for raw_way in self.reader.read_raw_ways():
            highway = raw_way.tags.get("highway")
            if highway and highway in ROAD_HIGHWAY_TYPES:
                road = transform_road(raw_way.osm_id, raw_way.tags, raw_way.coords)
                count += 1
                yield road

        logger.info("Extracted roads", count=count)

    def extract_pois(self) -> Iterator[POI]:
        """Extract and transform POIs from OSM data.

        Filters raw nodes to only include those with POI-related tags
        (amenity, shop, tourism) and transforms them into POI domain entities.

        Yields:
            POI domain entities
        """
        logger.info("Extracting POIs from OSM data")
        count = 0

        for raw_node in self.reader.read_raw_nodes():
            if any(tag in raw_node.tags for tag in POI_TAGS):
                poi = transform_poi(
                    raw_node.osm_id,
                    raw_node.tags,
                    raw_node.lon,
                    raw_node.lat,
                )
                count += 1
                yield poi

        logger.info("Extracted POIs", count=count)

    def extract_zones(self) -> Iterator[Zone]:
        """Extract and transform administrative zones from OSM data.

        Filters raw relations to only include administrative boundaries
        and transforms them into Zone domain entities.

        Yields:
            Zone domain entities (only valid ones with proper admin_level)
        """
        logger.info("Extracting zones from OSM data")
        count = 0

        for raw_relation in self.reader.read_raw_relations():
            if raw_relation.tags.get("boundary") == "administrative":
                zone = transform_zone(
                    raw_relation.osm_id,
                    raw_relation.tags,
                    raw_relation.coords,
                )
                if zone is not None:
                    count += 1
                    yield zone

        logger.info("Extracted zones", count=count)
