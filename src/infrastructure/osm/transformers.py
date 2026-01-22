"""Transform OSM raw data to domain entities.

This module contains transformation logic that converts raw OSM data
(from the infrastructure layer) into domain entities.
"""

from domain import (
    Road,
    POI,
    Zone,
    Coordinates,
    RoadType,
    Surface,
    Smoothness,
    POICategory,
    Address,
    OperatingHours,
)


def parse_road_type(highway: str) -> RoadType:
    """Convert OSM highway tag to RoadType enum."""
    mapping = {
        "motorway": RoadType.MOTORWAY,
        "motorway_link": RoadType.MOTORWAY,
        "trunk": RoadType.TRUNK,
        "trunk_link": RoadType.TRUNK,
        "primary": RoadType.PRIMARY,
        "primary_link": RoadType.PRIMARY,
        "secondary": RoadType.SECONDARY,
        "secondary_link": RoadType.SECONDARY,
        "tertiary": RoadType.TERTIARY,
        "tertiary_link": RoadType.TERTIARY,
        "residential": RoadType.RESIDENTIAL,
        "living_street": RoadType.RESIDENTIAL,
        "unclassified": RoadType.UNCLASSIFIED,
        "track": RoadType.TRACK,
        "path": RoadType.PATH,
        "footway": RoadType.PATH,
        "cycleway": RoadType.PATH,
    }
    return mapping.get(highway, RoadType.UNCLASSIFIED)


def parse_surface(surface: str | None) -> Surface:
    """Convert OSM surface tag to Surface enum."""
    if not surface:
        return Surface.UNKNOWN

    mapping = {
        "asphalt": Surface.ASPHALT,
        "paved": Surface.PAVED,
        "concrete": Surface.CONCRETE,
        "concrete:plates": Surface.CONCRETE,
        "concrete:lanes": Surface.CONCRETE,
        "gravel": Surface.GRAVEL,
        "fine_gravel": Surface.GRAVEL,
        "compacted": Surface.GRAVEL,
        "dirt": Surface.DIRT,
        "earth": Surface.DIRT,
        "mud": Surface.DIRT,
        "sand": Surface.SAND,
        "unpaved": Surface.UNPAVED,
        "ground": Surface.GROUND,
        "grass": Surface.GROUND,
    }
    return mapping.get(surface.lower(), Surface.UNKNOWN)


def parse_smoothness(smoothness: str | None) -> Smoothness:
    """Convert OSM smoothness tag to Smoothness enum."""
    if not smoothness:
        return Smoothness.UNKNOWN

    mapping = {
        "excellent": Smoothness.EXCELLENT,
        "good": Smoothness.GOOD,
        "intermediate": Smoothness.INTERMEDIATE,
        "bad": Smoothness.BAD,
        "very_bad": Smoothness.VERY_BAD,
        "horrible": Smoothness.HORRIBLE,
        "very_horrible": Smoothness.HORRIBLE,
        "impassable": Smoothness.IMPASSABLE,
    }
    return mapping.get(smoothness.lower(), Smoothness.UNKNOWN)


def parse_oneway(tags: dict[str, str]) -> bool:
    """Parse oneway tag."""
    oneway = tags.get("oneway", "no")
    return oneway in ("yes", "true", "1", "-1")


def parse_lanes(tags: dict[str, str]) -> int:
    """Parse lanes tag, defaulting to 2."""
    try:
        return int(tags.get("lanes", "2"))
    except ValueError:
        return 2


def parse_max_speed(tags: dict[str, str]) -> int | None:
    """Parse maxspeed tag (handles 'XX km/h' format)."""
    maxspeed = tags.get("maxspeed")
    if not maxspeed:
        return None

    # Remove common suffixes
    maxspeed = maxspeed.replace(" km/h", "").replace("km/h", "").replace(" mph", "")
    try:
        return int(maxspeed)
    except ValueError:
        return None


def transform_road(
    id: int,
    tags: dict[str, str],
    coords: list[tuple[float, float]],
) -> Road:
    """Transform OSM way data to Road entity.

    Args:
        id: OSM way ID
        tags: OSM tags dictionary
        coords: List of (lon, lat) coordinate tuples

    Returns:
        Road domain entity
    """
    geometry = [Coordinates(lat=lat, lon=lon) for lon, lat in coords]

    return Road(
        id=id,
        geometry=geometry,
        road_type=parse_road_type(tags.get("highway", "")),
        surface=parse_surface(tags.get("surface")),
        smoothness=parse_smoothness(tags.get("smoothness")),
        name=tags.get("name"),
        lanes=parse_lanes(tags),
        oneway=parse_oneway(tags),
        max_speed=parse_max_speed(tags),
        tags=tags,
    )


def categorize_poi(tags: dict[str, str]) -> tuple[POICategory, str]:
    """Determine POI category and subcategory from tags."""
    amenity = tags.get("amenity")
    shop = tags.get("shop")
    tourism = tags.get("tourism")

    # Transport
    if amenity in ("fuel", "parking", "bus_station", "taxi", "car_rental", "ferry_terminal"):
        return POICategory.TRANSPORT, amenity

    # Food
    if amenity in ("restaurant", "cafe", "fast_food", "bar", "food_court", "pub"):
        return POICategory.FOOD, amenity

    # Lodging
    if amenity in ("hotel", "guest_house", "motel", "hostel"):
        return POICategory.LODGING, amenity
    if tourism in ("hotel", "guest_house", "motel", "hostel", "camp_site"):
        return POICategory.LODGING, tourism

    # Health
    if amenity in ("hospital", "pharmacy", "clinic", "doctors", "dentist"):
        return POICategory.HEALTH, amenity

    # Services
    if amenity in ("bank", "atm", "post_office", "bureau_de_change", "money_transfer"):
        return POICategory.SERVICES, amenity

    # Government
    if amenity in ("police", "embassy", "townhall", "courthouse"):
        return POICategory.GOVERNMENT, amenity

    # Education
    if amenity in ("school", "university", "college", "library", "kindergarten"):
        return POICategory.EDUCATION, amenity

    # Shopping
    if shop:
        return POICategory.SHOPPING, shop

    return POICategory.UNKNOWN, amenity or shop or tourism or "unknown"


def normalize_text(text: str | None) -> str | None:
    """Normalize text for searching (lowercase, trim, remove extra spaces)."""
    if not text:
        return None
    import re
    normalized = text.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized if normalized else None


def build_search_text(name: str | None, tags: dict[str, str]) -> str:
    """Build best-effort search text from POI fields.
    
    Combines name, brand, operator, old_name from tags. Falls back to
    amenity/shop/tourism if no name-like fields are present.
    """
    parts = []
    
    if name:
        parts.append(name)
    
    for key in ["brand", "operator", "old_name"]:
        if key in tags and tags[key]:
            parts.append(tags[key])
    
    # If no name-like fields, use category tags
    if not parts:
        for key in ["amenity", "shop", "tourism"]:
            if key in tags and tags[key]:
                parts.append(tags[key])
                break
    
    # Last resort
    if not parts:
        parts.append("unknown")
    
    return " ".join(parts).strip()


def transform_poi(
    id: int,
    tags: dict[str, str],
    lon: float,
    lat: float,
) -> POI:
    """Transform OSM node/way data to POI entity.

    Args:
        id: OSM node/way ID
        tags: OSM tags dictionary
        lon: Longitude
        lat: Latitude

    Returns:
        POI domain entity
    """
    category, subcategory = categorize_poi(tags)
    address = Address.from_osm_tags(tags)

    opening_hours = None
    if "opening_hours" in tags:
        try:
            opening_hours = OperatingHours.parse(tags["opening_hours"])
        except Exception:
            pass  # Skip unparseable hours

    name = tags.get("name")
    has_name = bool(name and name.strip())
    name_normalized = normalize_text(name)
    search_text = build_search_text(name, tags)
    search_text_normalized = normalize_text(search_text)

    return POI(
        id=id,
        coordinates=Coordinates(lat=lat, lon=lon),
        category=category,
        subcategory=subcategory,
        name=name,
        address=address if not address.is_empty else None,
        phone=tags.get("phone") or tags.get("contact:phone"),
        opening_hours=opening_hours,
        website=tags.get("website") or tags.get("contact:website"),
        tags=tags,
        name_normalized=name_normalized,
        search_text=search_text,
        search_text_normalized=search_text_normalized,
        has_name=has_name,
        popularity=0,  # Will be updated later based on usage
    )


def parse_zone_type(level: str | None) -> tuple[str | None, int | None]:
    """Map OSM admin_level to a zone type string and hierarchy level.
    
    Returns:
        Tuple of (zone_type, level) or (None, None) if invalid
    """
    if not level:
        return None, None

    mapping = {
        "2": ("country", 0),
        "4": ("region", 1),
        "6": ("district", 2),
        "8": ("commune", 3),
        "10": ("fokontany", 4),
    }
    return mapping.get(level.strip(), (None, None))


def transform_zone(
    id: int,
    tags: dict[str, str],
    coords: list[tuple[float, float]],
) -> Zone | None:
    """Transform OSM relation data to Zone entity.

    Args:
        id: OSM relation ID
        tags: OSM tags dictionary
        coords: List of (lon, lat) coordinate tuples for outer ring

    Returns:
        Zone domain entity or None if invalid
    """
    zone_type, level = parse_zone_type(tags.get("admin_level"))
    if zone_type is None or level is None:
        return None

    name = tags.get("name")
    if not name:
        return None

    geometry = [Coordinates(lat=lat, lon=lon) for lon, lat in coords]
    if len(geometry) < 3:
        return None

    population = None
    if "population" in tags:
        try:
            population = int(tags["population"])
        except ValueError:
            pass

    return Zone(
        id=id,
        geometry=geometry,
        zone_type=zone_type,
        name=name,
        level=level,
        iso_code=tags.get("ISO3166-2"),
        population=population,
        parent_zone_id=None,  # Will be computed later via spatial containment
        tags=tags,
    )
