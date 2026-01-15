"""Administrative zone entity."""

from dataclasses import dataclass, field
from enum import IntEnum
from math import cos, degrees, radians

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

    @property
    def area(self) -> float:
        """Approximate polygon area in square meters (equirectangular projection)."""
        area, _ = self._planar_area_and_centroid()
        return area

    @property
    def centroid(self) -> Coordinates:
        """Approximate polygon centroid (lat/lon)."""
        _, centroid = self._planar_area_and_centroid()
        return centroid

    def _planar_area_and_centroid(self) -> tuple[float, Coordinates]:
        """Compute area and centroid using a simple planar projection."""
        coords = self.geometry
        if coords[0] != coords[-1]:
            coords = [*coords, coords[0]]

        lats = [c.lat for c in coords]
        lat0 = radians(sum(lats) / len(lats))

        R = 6_371_000.0  # Earth radius in meters
        points = [
            (radians(c.lon) * R * cos(lat0), radians(c.lat) * R) for c in coords
        ]

        area2 = 0.0
        cx = 0.0
        cy = 0.0
        for i in range(len(points) - 1):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]
            cross = x0 * y1 - x1 * y0
            area2 += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross

        if area2 == 0.0:
            return 0.0, coords[0]

        area = abs(area2) / 2.0
        cx /= 3.0 * area2
        cy /= 3.0 * area2

        lon = degrees(cx / (R * cos(lat0)))
        lat = degrees(cy / R)
        return area, Coordinates(lat=lat, lon=lon)
