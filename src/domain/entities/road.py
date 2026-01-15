"""Road entity."""

from dataclasses import dataclass, field

from domain.enums import RoadType, Surface, Smoothness
from domain.value_objects import Coordinates, RoadPenalty


@dataclass(slots=True)
class Road:
    """Road entity representing an OSM way with highway tag.

    Attributes:
        osm_id: Unique OSM identifier for versioning
        geometry: List of coordinates forming the road LineString
        road_type: Classification (primary, secondary, etc.)
        surface: Road surface material
        smoothness: Road surface condition
        name: Road name (optional)
        lanes: Number of lanes (default 2)
        oneway: One-way restriction
        max_speed: Speed limit in km/h (optional)
    """

    osm_id: int
    geometry: list[Coordinates]
    road_type: RoadType
    surface: Surface = Surface.UNKNOWN
    smoothness: Smoothness = Smoothness.UNKNOWN
    name: str | None = None
    lanes: int = 2
    oneway: bool = False
    max_speed: int | None = None
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate road has at least 2 points."""
        if len(self.geometry) < 2:
            raise ValueError("Road must have at least 2 coordinate points")

    @property
    def length(self) -> float:
        """Calculate total road length in meters."""
        total = 0.0
        for i in range(len(self.geometry) - 1):
            total += self.geometry[i].distance_to(self.geometry[i + 1])
        return total

    @property
    def start(self) -> Coordinates:
        """First coordinate of the road."""
        return self.geometry[0]

    @property
    def end(self) -> Coordinates:
        """Last coordinate of the road."""
        return self.geometry[-1]

    @property
    def default_speed_kmh(self) -> int:
        """Get default speed based on road type (Madagascar context)."""
        defaults = {
            RoadType.MOTORWAY: 110,
            RoadType.TRUNK: 90,
            RoadType.PRIMARY: 80,
            RoadType.SECONDARY: 60,
            RoadType.TERTIARY: 50,
            RoadType.RESIDENTIAL: 30,
            RoadType.UNCLASSIFIED: 40,
            RoadType.TRACK: 20,
            RoadType.PATH: 10,
        }
        return defaults.get(self.road_type, 40)

    @property
    def effective_speed_kmh(self) -> int:
        """Get max_speed if set, otherwise default speed."""
        return self.max_speed if self.max_speed else self.default_speed_kmh

    @property
    def penalty(self) -> RoadPenalty:
        """Compute penalty factors for this road based on surface and smoothness."""
        return RoadPenalty.from_road_attributes(
            surface=self.surface,
            smoothness=self.smoothness,
            is_rainy_season=False,
        )

    @property
    def surface_factor(self) -> float:
        """Penalty factor for the road surface."""
        return self.penalty.surface_factor

    @property
    def smoothness_factor(self) -> float:
        """Penalty factor for the road smoothness."""
        return self.penalty.smoothness_factor

    @property
    def penalized_speed_kmh(self) -> float:
        """Speed after applying penalty factors to the effective speed."""
        return self.penalty.apply_to_speed(self.effective_speed_kmh)
