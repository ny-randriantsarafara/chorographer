"""Road penalty value object for speed calculations."""

from dataclasses import dataclass

from domain.enums import Surface, Smoothness


# Default penalty factors by surface type
SURFACE_FACTORS: dict[Surface, float] = {
    Surface.ASPHALT: 1.0,
    Surface.PAVED: 1.0,
    Surface.CONCRETE: 1.0,
    Surface.GRAVEL: 0.7,
    Surface.DIRT: 0.4,
    Surface.SAND: 0.3,
    Surface.UNPAVED: 0.5,
    Surface.GROUND: 0.4,
    Surface.UNKNOWN: 0.6,
}

# Default penalty factors by smoothness
SMOOTHNESS_FACTORS: dict[Smoothness, float] = {
    Smoothness.EXCELLENT: 1.0,
    Smoothness.GOOD: 0.9,
    Smoothness.INTERMEDIATE: 0.7,
    Smoothness.BAD: 0.5,
    Smoothness.VERY_BAD: 0.3,
    Smoothness.HORRIBLE: 0.2,
    Smoothness.IMPASSABLE: 0.0,
    Smoothness.UNKNOWN: 0.7,
}

# Rainy season factor for unpaved roads (Nov-Apr in Madagascar)
RAINY_SEASON_UNPAVED_FACTOR = 0.6


@dataclass(frozen=True, slots=True)
class RoadPenalty:
    """Immutable road penalty factors for speed calculation.

    Effective speed = base_speed × surface_factor × smoothness_factor × rainy_season_factor
    """

    surface_factor: float = 1.0
    smoothness_factor: float = 1.0
    rainy_season_factor: float = 1.0

    def __post_init__(self) -> None:
        """Validate factors are in valid range."""
        for name, value in [
            ("surface_factor", self.surface_factor),
            ("smoothness_factor", self.smoothness_factor),
            ("rainy_season_factor", self.rainy_season_factor),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")

    @property
    def effective_multiplier(self) -> float:
        """Calculate combined speed multiplier."""
        return self.surface_factor * self.smoothness_factor * self.rainy_season_factor

    def apply_to_speed(self, base_speed: float) -> float:
        """Apply penalty to a base speed, returning effective speed in km/h."""
        return base_speed * self.effective_multiplier

    @classmethod
    def from_road_attributes(
        cls,
        surface: Surface,
        smoothness: Smoothness,
        is_rainy_season: bool = False,
    ) -> "RoadPenalty":
        """Create penalty from road surface and smoothness attributes."""
        surface_factor = SURFACE_FACTORS.get(surface, 0.6)
        smoothness_factor = SMOOTHNESS_FACTORS.get(smoothness, 0.7)

        # Apply rainy season penalty to unpaved roads
        rainy_factor = 1.0
        if is_rainy_season and surface not in (Surface.ASPHALT, Surface.PAVED, Surface.CONCRETE):
            rainy_factor = RAINY_SEASON_UNPAVED_FACTOR

        return cls(
            surface_factor=surface_factor,
            smoothness_factor=smoothness_factor,
            rainy_season_factor=rainy_factor,
        )
