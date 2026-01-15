"""Point of Interest entity."""

from dataclasses import dataclass, field

from domain.enums import POICategory
from domain.value_objects import Coordinates, Address, OperatingHours


@dataclass(slots=True)
class POI:
    """Point of Interest entity.

    Attributes:
        osm_id: Unique OSM identifier
        coordinates: Location
        category: High-level category (transport, food, etc.)
        subcategory: Specific type (fuel, restaurant, etc.)
        name: Business name (optional)
        address: Street address (optional)
        phone: Contact phone (optional)
        opening_hours: Business hours (optional)
        price_range: 1-4 scale (optional, from scraping)
        website: URL (optional)
    """

    osm_id: int
    coordinates: Coordinates
    category: POICategory
    subcategory: str
    name: str | None = None
    address: Address | None = None
    phone: str | None = None
    opening_hours: OperatingHours | None = None
    price_range: int | None = None
    website: str | None = None
    tags: dict[str, str] = field(default_factory=dict)

    @classmethod
    def categorize(cls, amenity: str | None, shop: str | None) -> tuple[POICategory, str]:
        """Determine category and subcategory from OSM tags."""
        # Transport
        if amenity in ("fuel", "parking", "bus_station", "taxi", "car_rental"):
            return POICategory.TRANSPORT, amenity

        # Food
        if amenity in ("restaurant", "cafe", "fast_food", "bar", "food_court"):
            return POICategory.FOOD, amenity

        # Lodging
        if amenity in ("hotel", "guest_house", "motel", "hostel"):
            return POICategory.LODGING, amenity

        # Health
        if amenity in ("hospital", "pharmacy", "clinic", "doctors", "dentist"):
            return POICategory.HEALTH, amenity

        # Services
        if amenity in ("bank", "atm", "post_office", "bureau_de_change"):
            return POICategory.SERVICES, amenity

        # Government
        if amenity in ("police", "embassy", "townhall", "courthouse"):
            return POICategory.GOVERNMENT, amenity

        # Education
        if amenity in ("school", "university", "college", "library"):
            return POICategory.EDUCATION, amenity

        # Shopping (from shop tag)
        if shop:
            if shop in ("supermarket", "convenience", "mall", "department_store"):
                return POICategory.SHOPPING, shop
            if shop in ("pharmacy",):
                return POICategory.HEALTH, shop
            return POICategory.SHOPPING, shop

        # Default
        return POICategory.UNKNOWN, amenity or shop or "unknown"
