"""Domain layer - Core business logic."""

from domain.entities import Road, POI, Zone, Segment
from domain.services import split_roads_into_segments
from domain.value_objects import Coordinates, RoadPenalty, OperatingHours, TimeRange, Address
from domain.enums import RoadType, Surface, Smoothness, POICategory
from domain.exceptions import (
    DomainError,
    ExtractionError,
    TransformationError,
    ValidationError,
    PenaltyCalculationError,
)

__all__ = [
    # Entities
    "Road",
    "POI",
    "Zone",
    "Segment",
    "split_roads_into_segments",
    # Value Objects
    "Coordinates",
    "RoadPenalty",
    "OperatingHours",
    "TimeRange",
    "Address",
    # Enums
    "RoadType",
    "Surface",
    "Smoothness",
    "POICategory",
    # Exceptions
    "DomainError",
    "ExtractionError",
    "TransformationError",
    "ValidationError",
    "PenaltyCalculationError",
]
