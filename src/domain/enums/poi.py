"""POI-related enums."""

from enum import Enum


class POICategory(Enum):
    """Point of Interest category classification."""

    TRANSPORT = "transport"  # fuel, parking, bus_station
    FOOD = "food"  # restaurant, cafe, fast_food
    LODGING = "lodging"  # hotel, guest_house, motel
    SERVICES = "services"  # bank, atm, post_office
    HEALTH = "health"  # hospital, pharmacy, clinic
    SHOPPING = "shopping"  # supermarket, convenience, market
    EDUCATION = "education"  # school, university
    GOVERNMENT = "government"  # police, embassy
    UNKNOWN = "unknown"
