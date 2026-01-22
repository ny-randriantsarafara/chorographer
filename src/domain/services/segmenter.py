"""Build routing segments by splitting roads at intersections."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Iterable

from domain.entities import Road, Segment
from domain.value_objects import RoadPenalty, Coordinates


def _segment_id(road_id: int, start: Coordinates, end: Coordinates) -> int:
    """Generate a stable segment id based on endpoints."""
    payload = f"{road_id}:{start.lat}:{start.lon}:{end.lat}:{end.lon}".encode("utf-8")
    digest = hashlib.sha1(payload).digest()[:8]
    value = int.from_bytes(digest, byteorder="big", signed=False)
    return value & 0x7FFF_FFFF_FFFF_FFFF


def split_roads_into_segments(roads: Iterable[Road]) -> list[Segment]:
    """Split roads at shared coordinates to form routing segments."""
    road_list = list(roads)
    if not road_list:
        return []

    coord_counts: dict[tuple[float, float], int] = defaultdict(int)
    for road in road_list:
        for coord in road.geometry:
            coord_counts[(coord.lat, coord.lon)] += 1

    segments: list[Segment] = []
    for road in road_list:
        breakpoints: list[int] = []
        for idx, coord in enumerate(road.geometry):
            key = (coord.lat, coord.lon)
            if idx == 0 or idx == len(road.geometry) - 1 or coord_counts[key] > 1:
                breakpoints.append(idx)

        if len(breakpoints) < 2:
            continue

        penalty = RoadPenalty.from_road_attributes(
            surface=road.surface,
            smoothness=road.smoothness,
            is_rainy_season=False,
        )
        base_speed = road.effective_speed_kmh

        for i in range(len(breakpoints) - 1):
            start_idx = breakpoints[i]
            end_idx = breakpoints[i + 1]
            if end_idx - start_idx < 1:
                continue

            coords = road.geometry[start_idx : end_idx + 1]
            length = 0.0
            for j in range(len(coords) - 1):
                length += coords[j].distance_to(coords[j + 1])

            start = coords[0]
            end = coords[-1]
            segment = Segment(
                id=_segment_id(road.id, start, end),
                road_id=road.id,
                start=start,
                end=end,
                length=length,
                penalty=penalty,
                oneway=road.oneway,
                base_speed=base_speed,
            )
            segments.append(segment)

    return segments
