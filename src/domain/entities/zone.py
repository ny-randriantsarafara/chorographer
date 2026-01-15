"""Administrative zone entity."""

from dataclasses import dataclass, field
from enum import IntEnum

from domain.value_objects import Coordinates


class AdminLevel(IntEnum):
    """OSM admin_level values for Madagascar."""

    COUNTRY = 2  # Madagascar
    REGION = 4  # Faritra (22 regions)
    DISTRICT = 6  # Distrika
    COMMUNE = 8  # Kaominina
    FOKONTANY = 10  # Fokontany (neighborhood)


@dataclass(slots=True)
class Zone:
    """Administrative boundary zone.

    Attributes:
        osm_id: Unique OSM identifier
        geometry: List of coordinates forming the polygon boundary
        admin_level: Administrative level (4=region, 6=district, 8=commune)
        name: Official name
        malagasy_name: Malagasy name (optional)
        iso_code: ISO 3166-2 code (optional, e.g., MG-A for Antananarivo)
        population: Population count (optional)
    """

    osm_id: int
    geometry: list[Coordinates]
    admin_level: AdminLevel
    name: str
    malagasy_name: str | None = None
    iso_code: str | None = None
    population: int | None = None
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate zone has at least 3 points (triangle)."""
        if len(self.geometry) < 3:
            raise ValueError("Zone must have at least 3 coordinate points")

    @property
    def is_region(self) -> bool:
        """Check if this is a region-level zone."""
        return self.admin_level == AdminLevel.REGION

    @property
    def is_district(self) -> bool:
        """Check if this is a district-level zone."""
        return self.admin_level == AdminLevel.DISTRICT

    @property
    def is_town(self) -> bool:
        """Check if this is a commune-level zone."""
        return self.admin_level == AdminLevel.COMMUNE

    def contains_point(self, point: Coordinates) -> bool:
        """Check if a point is inside this zone (ray casting algorithm)."""
        x, y = point.lon, point.lat
        n = len(self.geometry)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = self.geometry[i].lon, self.geometry[i].lat
            xj, yj = self.geometry[j].lon, self.geometry[j].lat

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside
