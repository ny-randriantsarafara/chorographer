"""Coordinates value object."""

from dataclasses import dataclass
from math import radians, sin, cos, sqrt, atan2


@dataclass(frozen=True, slots=True)
class Coordinates:
    """Immutable lat/lon coordinate pair."""

    lat: float
    lon: float

    def __post_init__(self) -> None:
        """Validate coordinate bounds."""
        if not -90 <= self.lat <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.lat}")
        if not -180 <= self.lon <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.lon}")

    def distance_to(self, other: "Coordinates") -> float:
        """Calculate distance to another point in meters using Haversine formula."""
        R = 6_371_000  # Earth's radius in meters

        lat1, lon1 = radians(self.lat), radians(self.lon)
        lat2, lon2 = radians(other.lat), radians(other.lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def as_tuple(self) -> tuple[float, float]:
        """Return as (lat, lon) tuple."""
        return (self.lat, self.lon)

    def as_geojson(self) -> list[float]:
        """Return as GeoJSON [lon, lat] format."""
        return [self.lon, self.lat]
