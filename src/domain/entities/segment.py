"""Road segment entity for routing graph."""

from dataclasses import dataclass

from domain.value_objects import Coordinates, RoadPenalty


@dataclass(slots=True)
class Segment:
    """Road segment for routing graph.

    A segment is a portion of a road between two nodes (intersections or endpoints).
    Used to build the routing graph where roads are split at intersections.

    Attributes:
        id: Unique segment identifier
        road_id: Parent road OSM ID
        start: Start coordinate
        end: End coordinate
        length: Segment length in meters
        penalty: Speed penalty factors
        oneway: Whether this segment is one-way
        base_speed: Base speed limit for this segment
    """

    id: int
    road_id: int
    start: Coordinates
    end: Coordinates
    length: float
    penalty: RoadPenalty
    oneway: bool = False
    base_speed: int = 50

    @property
    def effective_speed_kmh(self) -> float:
        """Calculate effective speed after applying penalties."""
        return self.penalty.apply_to_speed(self.base_speed)

    @property
    def travel_time_seconds(self) -> float:
        """Calculate travel time in seconds."""
        speed_ms = self.effective_speed_kmh * 1000 / 3600  # km/h to m/s
        if speed_ms <= 0:
            return float("inf")
        return self.length / speed_ms

    @property
    def cost(self) -> float:
        """Routing cost (travel time in seconds). Used for pathfinding."""
        return self.travel_time_seconds

    def reverse(self) -> "Segment":
        """Create reversed segment (for bidirectional roads)."""
        return Segment(
            id=-self.id,  # Negative ID indicates reverse
            road_id=self.road_id,
            start=self.end,
            end=self.start,
            length=self.length,
            penalty=self.penalty,
            oneway=self.oneway,
            base_speed=self.base_speed,
        )
