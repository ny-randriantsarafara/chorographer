"""Raw OSM data types for infrastructure layer."""

from dataclasses import dataclass


@dataclass(slots=True)
class RawWay:
    """Raw OSM way data before transformation."""

    id: int
    tags: dict[str, str]
    coords: list[tuple[float, float]]  # (lon, lat) pairs


@dataclass(slots=True)
class RawNode:
    """Raw OSM node data before transformation."""

    id: int
    tags: dict[str, str]
    lon: float
    lat: float


@dataclass(slots=True)
class RawRelation:
    """Raw OSM relation data before transformation."""

    id: int
    tags: dict[str, str]
    coords: list[tuple[float, float]]  # outer ring (lon, lat) pairs
