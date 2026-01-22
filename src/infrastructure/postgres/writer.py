"""Async PostgreSQL writer for domain entities."""

import json
from collections.abc import Iterable
from typing import Any

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from application.ports.repository import GeoRepository
from domain import POI, Road, Segment, Zone
from infrastructure.logging import get_logger

logger = get_logger(__name__)


def _coords_to_wkt_linestring(coords: list[Any]) -> str:
    """Convert coordinates to WKT LineString."""
    points = ", ".join(f"{c.lon} {c.lat}" for c in coords)
    return f"SRID=4326;LINESTRING({points})"


def _coords_to_wkt_point(coord: Any) -> str:
    """Convert coordinate to WKT Point."""
    return f"SRID=4326;POINT({coord.lon} {coord.lat})"


def _coords_to_wkt_polygon(coords: list[Any]) -> str:
    """Convert coordinates to WKT Polygon."""
    points = ", ".join(f"{c.lon} {c.lat}" for c in coords)
    # Close the ring if not already closed
    if coords[0] != coords[-1]:
        points += f", {coords[0].lon} {coords[0].lat}"
    return f"SRID=4326;POLYGON(({points}))"


class PostgresWriter(GeoRepository):
    """Async writer for persisting domain entities to PostgreSQL.

    Implements the GeoRepository port from the application layer.

    Usage:
        async with create_pool(settings) as pool:
            writer = PostgresWriter(pool)
            count = await writer.save_roads(roads)
    """

    def __init__(self, pool: AsyncConnectionPool, batch_size: int = 1000) -> None:
        """Initialize writer.

        Args:
            pool: Async connection pool
            batch_size: Number of records per batch insert
        """
        self.pool = pool
        self.batch_size = batch_size

    def _road_to_tuple(self, road: Road) -> tuple[Any, ...]:
        """Convert Road entity to insert tuple."""
        return (
            road.id,
            _coords_to_wkt_linestring(road.geometry),
            road.road_type.value,
            road.surface.value if road.surface else None,
            road.smoothness.value if road.smoothness else None,
            road.name,
            road.lanes,
            road.oneway,
            road.max_speed,
            road.length,
            road.surface_factor,
            road.smoothness_factor,
            road.effective_speed_kmh,
            road.penalized_speed_kmh,
            json.dumps(road.tags) if road.tags else None,
        )

    async def save_roads(self, roads: Iterable[Road]) -> int:
        """Batch insert roads into database.

        Args:
            roads: Iterable of Road entities

        Returns:
            Number of roads saved
        """
        count = 0
        batch: list[tuple[Any, ...]] = []

        async with self.pool.connection() as conn:
            for road in roads:
                batch.append(self._road_to_tuple(road))

                if len(batch) >= self.batch_size:
                    count += await self._insert_roads_batch(conn, batch)
                    batch = []

            # Insert remaining
            if batch:
                count += await self._insert_roads_batch(conn, batch)

        logger.info("Written roads", count=count)
        return count

    async def save_roads_batch(self, roads: list[Road]) -> int:
        """Insert a pre-batched list of roads.

        Used by AsyncBatcher for parallel processing.

        Args:
            roads: List of Road entities (already batched)

        Returns:
            Number of roads saved
        """
        if not roads:
            return 0

        async with self.pool.connection() as conn:
            batch = [self._road_to_tuple(road) for road in roads]
            return await self._insert_roads_batch(conn, batch)

    async def _insert_roads_batch(
        self,
        conn: AsyncConnection,
        batch: list[tuple[Any, ...]],
    ) -> int:
        """Insert a batch of roads."""
        query = """
            INSERT INTO roads (
                id, geometry, road_type, surface, smoothness,
                name, lanes, oneway, max_speed,
                length, surface_factor, smoothness_factor,
                effective_speed_kmh, penalized_speed_kmh, tags
            )
            VALUES (%s, ST_GeomFromEWKT(%s), %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                geometry = EXCLUDED.geometry,
                road_type = EXCLUDED.road_type,
                surface = EXCLUDED.surface,
                smoothness = EXCLUDED.smoothness,
                name = EXCLUDED.name,
                lanes = EXCLUDED.lanes,
                oneway = EXCLUDED.oneway,
                max_speed = EXCLUDED.max_speed,
                length = EXCLUDED.length,
                surface_factor = EXCLUDED.surface_factor,
                smoothness_factor = EXCLUDED.smoothness_factor,
                effective_speed_kmh = EXCLUDED.effective_speed_kmh,
                penalized_speed_kmh = EXCLUDED.penalized_speed_kmh,
                tags = EXCLUDED.tags,
                updated_at = NOW()
        """
        async with conn.cursor() as cur:
            await cur.executemany(query, batch)
        await conn.commit()
        return len(batch)

    def _poi_to_tuple(self, poi: POI) -> tuple[Any, ...]:
        """Convert POI entity to insert tuple."""
        address_json = None
        if poi.address:
            address_json = json.dumps({
                "street": poi.address.street,
                "housenumber": poi.address.housenumber,
                "city": poi.address.city,
                "postcode": poi.address.postcode,
            })

        return (
            poi.id,
            _coords_to_wkt_point(poi.coordinates),
            poi.category.value,
            poi.subcategory,
            poi.name,
            address_json,
            poi.phone,
            poi.opening_hours.raw if poi.opening_hours else None,
            poi.price_range,
            poi.website,
            poi.is_24_7,
            poi.formatted_address,
            poi.name_normalized,
            poi.search_text,
            poi.search_text_normalized,
            poi.has_name,
            poi.popularity,
            json.dumps(poi.tags) if poi.tags else None,
        )

    async def save_pois(self, pois: Iterable[POI]) -> int:
        """Batch insert POIs into database.

        Args:
            pois: Iterable of POI entities

        Returns:
            Number of POIs saved
        """
        count = 0
        batch: list[tuple[Any, ...]] = []

        async with self.pool.connection() as conn:
            for poi in pois:
                batch.append(self._poi_to_tuple(poi))

                if len(batch) >= self.batch_size:
                    count += await self._insert_pois_batch(conn, batch)
                    batch = []

            if batch:
                count += await self._insert_pois_batch(conn, batch)

        logger.info("Written POIs", count=count)
        return count

    async def save_pois_batch(self, pois: list[POI]) -> int:
        """Insert a pre-batched list of POIs.

        Used by AsyncBatcher for parallel processing.

        Args:
            pois: List of POI entities (already batched)

        Returns:
            Number of POIs saved
        """
        if not pois:
            return 0

        async with self.pool.connection() as conn:
            batch = [self._poi_to_tuple(poi) for poi in pois]
            return await self._insert_pois_batch(conn, batch)

    async def _insert_pois_batch(
        self,
        conn: AsyncConnection,
        batch: list[tuple[Any, ...]],
    ) -> int:
        """Insert a batch of POIs."""
        query = """
            INSERT INTO pois (
                id, geometry, category, subcategory, name,
                address, phone, opening_hours, price_range, website,
                is_24_7, formatted_address,
                name_normalized, search_text, search_text_normalized, has_name, popularity,
                tags
            )
            VALUES (%s, ST_GeomFromEWKT(%s), %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                geometry = EXCLUDED.geometry,
                category = EXCLUDED.category,
                subcategory = EXCLUDED.subcategory,
                name = EXCLUDED.name,
                address = EXCLUDED.address,
                phone = EXCLUDED.phone,
                opening_hours = EXCLUDED.opening_hours,
                price_range = EXCLUDED.price_range,
                website = EXCLUDED.website,
                is_24_7 = EXCLUDED.is_24_7,
                formatted_address = EXCLUDED.formatted_address,
                name_normalized = EXCLUDED.name_normalized,
                search_text = EXCLUDED.search_text,
                search_text_normalized = EXCLUDED.search_text_normalized,
                has_name = EXCLUDED.has_name,
                popularity = EXCLUDED.popularity,
                tags = EXCLUDED.tags,
                updated_at = NOW()
        """
        async with conn.cursor() as cur:
            await cur.executemany(query, batch)
        await conn.commit()
        return len(batch)

    def _zone_to_tuple(self, zone: Zone) -> tuple[Any, ...]:
        """Convert Zone entity to insert tuple."""
        return (
            zone.id,
            _coords_to_wkt_polygon(zone.geometry),
            zone.zone_type,
            zone.name,
            zone.level,
            zone.parent_zone_id,
            zone.iso_code,
            zone.population,
            zone.area,
            _coords_to_wkt_point(zone.centroid),
            json.dumps(zone.tags) if zone.tags else None,
        )

    async def save_zones(self, zones: Iterable[Zone]) -> int:
        """Batch insert zones into database.

        Args:
            zones: Iterable of Zone entities

        Returns:
            Number of zones saved
        """
        count = 0
        batch: list[tuple[Any, ...]] = []

        async with self.pool.connection() as conn:
            for zone in zones:
                batch.append(self._zone_to_tuple(zone))

                if len(batch) >= self.batch_size:
                    count += await self._insert_zones_batch(conn, batch)
                    batch = []

            if batch:
                count += await self._insert_zones_batch(conn, batch)

        logger.info("Written zones", count=count)
        return count

    async def save_zones_batch(self, zones: list[Zone]) -> int:
        """Insert a pre-batched list of zones.

        Used by AsyncBatcher for parallel processing.

        Args:
            zones: List of Zone entities (already batched)

        Returns:
            Number of zones saved
        """
        if not zones:
            return 0

        async with self.pool.connection() as conn:
            batch = [self._zone_to_tuple(zone) for zone in zones]
            return await self._insert_zones_batch(conn, batch)

    async def _insert_zones_batch(
        self,
        conn: AsyncConnection,
        batch: list[tuple[Any, ...]],
    ) -> int:
        """Insert a batch of zones."""
        query = """
            INSERT INTO zones (
                id, geometry, zone_type, name, level, parent_zone_id,
                iso_code, population, area, centroid, tags
            )
            VALUES (%s, ST_Multi(ST_GeomFromEWKT(%s)), %s, %s, %s, %s, %s, %s,
                    %s, ST_GeomFromEWKT(%s), %s)
            ON CONFLICT (id) DO UPDATE SET
                geometry = EXCLUDED.geometry,
                zone_type = EXCLUDED.zone_type,
                name = EXCLUDED.name,
                level = EXCLUDED.level,
                parent_zone_id = EXCLUDED.parent_zone_id,
                iso_code = EXCLUDED.iso_code,
                population = EXCLUDED.population,
                area = EXCLUDED.area,
                centroid = EXCLUDED.centroid,
                tags = EXCLUDED.tags,
                updated_at = NOW()
        """
        async with conn.cursor() as cur:
            await cur.executemany(query, batch)
        await conn.commit()
        return len(batch)

    def _segment_to_tuple(self, segment: Segment) -> tuple[Any, ...]:
        """Convert Segment entity to insert tuple."""
        return (
            segment.id,
            segment.road_id,
            _coords_to_wkt_linestring([segment.start, segment.end]),
            _coords_to_wkt_point(segment.start),
            _coords_to_wkt_point(segment.end),
            segment.length,
            segment.penalty.surface_factor,
            segment.penalty.smoothness_factor,
            segment.penalty.rainy_season_factor,
            segment.oneway,
            segment.base_speed,
            segment.effective_speed_kmh,
            segment.travel_time_seconds,
            segment.cost,
        )

    async def save_segments(self, segments: Iterable[Segment]) -> int:
        """Batch insert segments into database.

        Args:
            segments: Iterable of Segment entities

        Returns:
            Number of segments saved
        """
        count = 0
        batch: list[tuple[Any, ...]] = []

        async with self.pool.connection() as conn:
            for segment in segments:
                batch.append(self._segment_to_tuple(segment))

                if len(batch) >= self.batch_size:
                    count += await self._insert_segments_batch(conn, batch)
                    batch = []

            if batch:
                count += await self._insert_segments_batch(conn, batch)

        logger.info("Written segments", count=count)
        return count

    async def save_segments_batch(self, segments: list[Segment]) -> int:
        """Insert a pre-batched list of segments.

        Used by AsyncBatcher for parallel processing.

        Args:
            segments: List of Segment entities (already batched)

        Returns:
            Number of segments saved
        """
        if not segments:
            return 0

        async with self.pool.connection() as conn:
            batch = [self._segment_to_tuple(segment) for segment in segments]
            return await self._insert_segments_batch(conn, batch)

    async def _insert_segments_batch(
        self,
        conn: AsyncConnection,
        batch: list[tuple[Any, ...]],
    ) -> int:
        """Insert a batch of segments."""
        query = """
            INSERT INTO segments (
                id, road_id, geometry, start_point, end_point,
                length, surface_factor, smoothness_factor, rainy_season_factor,
                oneway, base_speed, effective_speed_kmh, travel_time_seconds, cost
            )
            VALUES (
                %s, %s, ST_GeomFromEWKT(%s), ST_GeomFromEWKT(%s), ST_GeomFromEWKT(%s),
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                road_id = EXCLUDED.road_id,
                geometry = EXCLUDED.geometry,
                start_point = EXCLUDED.start_point,
                end_point = EXCLUDED.end_point,
                length = EXCLUDED.length,
                surface_factor = EXCLUDED.surface_factor,
                smoothness_factor = EXCLUDED.smoothness_factor,
                rainy_season_factor = EXCLUDED.rainy_season_factor,
                oneway = EXCLUDED.oneway,
                base_speed = EXCLUDED.base_speed,
                effective_speed_kmh = EXCLUDED.effective_speed_kmh,
                travel_time_seconds = EXCLUDED.travel_time_seconds,
                cost = EXCLUDED.cost,
                updated_at = NOW()
        """
        async with conn.cursor() as cur:
            await cur.executemany(query, batch)
        await conn.commit()
        return len(batch)
