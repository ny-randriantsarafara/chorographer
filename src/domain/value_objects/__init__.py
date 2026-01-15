"""Domain value objects - Immutable domain values."""

from domain.value_objects.coordinates import Coordinates
from domain.value_objects.penalty import RoadPenalty
from domain.value_objects.operating_hours import OperatingHours, TimeRange
from domain.value_objects.address import Address

__all__ = [
    "Coordinates",
    "RoadPenalty",
    "OperatingHours",
    "TimeRange",
    "Address",
]
