"""Road-related enums."""

from enum import Enum


class RoadType(Enum):
    """OSM highway classification."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    RESIDENTIAL = "residential"
    TRACK = "track"
    UNCLASSIFIED = "unclassified"
    TRUNK = "trunk"
    MOTORWAY = "motorway"
    PATH = "path"


class Surface(Enum):
    """Road surface material."""

    ASPHALT = "asphalt"
    PAVED = "paved"
    CONCRETE = "concrete"
    GRAVEL = "gravel"
    DIRT = "dirt"
    SAND = "sand"
    UNPAVED = "unpaved"
    GROUND = "ground"
    UNKNOWN = "unknown"


class Smoothness(Enum):
    """Road surface quality/condition."""

    EXCELLENT = "excellent"
    GOOD = "good"
    INTERMEDIATE = "intermediate"
    BAD = "bad"
    VERY_BAD = "very_bad"
    HORRIBLE = "horrible"
    IMPASSABLE = "impassable"
    UNKNOWN = "unknown"
