"""Async PostgreSQL writer for domain entities."""

import json
from collections.abc import Iterable
from typing import Any

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from application.ports.repository import GeoRepository
from domain import Road, POI, Zone
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
                batch.append((
                    road.osm_id,
                    _coords_to_wkt_linestring(road.geometry),
                    road.road_type.value,
                    road.surface.value if road.surface else None,
                    road.smoothness.value if road.smoothness else None,
                    road.name,
                    road.lanes,
                    road.oneway,
                    road.max_speed,
                    json.dumps(road.tags) if road.tags else None,
                ))

                if len(batch) >= self.batch_size:
                    count += await self._insert_roads_batch(conn, batch)
                    batch = []

            # Insert remaining
            if batch:
                count += await self._insert_roads_batch(conn, batch)

        logger.info("Written roads", count=count)
        return count

    async def _insert_roads_batch(
        self,
        conn: AsyncConnection,
        batch: list[tuple[Any, ...]],
    ) -> int:
        """Insert a batch of roads."""
        query = """
            INSERT INTO roads (
                osm_id, geometry, road_type, surface, smoothness,
                name, lanes, oneway, max_speed, tags
            )
            VALUES (%s, ST_GeomFromEWKT(%s), %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (osm_id) DO UPDATE SET
                geometry = EXCLUDED.geometry,
                road_type = EXCLUDED.road_type,
                surface = EXCLUDED.surface,
                smoothness = EXCLUDED.smoothness,
                name = EXCLUDED.name,
                lanes = EXCLUDED.lanes,
                oneway = EXCLUDED.oneway,
                max_speed = EXCLUDED.max_speed,
                tags = EXCLUDED.tags,
                updated_at = NOW()
        """
        async with conn.cursor() as cur:
            await cur.executemany(query, batch)
        await conn.commit()
        return len(batch)

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
                address_json = None
                if poi.address:
                    address_json = json.dumps({
                        "street": poi.address.street,
                        "housenumber": poi.address.housenumber,
                        "city": poi.address.city,
                        "postcode": poi.address.postcode,
                    })

                batch.append((
                    poi.osm_id,
                    _coords_to_wkt_point(poi.coordinates),
                    poi.category.value,
                    poi.subcategory,
                    poi.name,
                    address_json,
                    poi.phone,
                    poi.opening_hours.raw if poi.opening_hours else None,
                    poi.price_range,
                    poi.website,
                    json.dumps(poi.tags) if poi.tags else None,
                ))

                if len(batch) >= self.batch_size:
                    count += await self._insert_pois_batch(conn, batch)
                    batch = []

            if batch:
                count += await self._insert_pois_batch(conn, batch)

        logger.info("Written POIs", count=count)
        return count

    async def _insert_pois_batch(
        self,
        conn: AsyncConnection,
        batch: list[tuple[Any, ...]],
    ) -> int:
        """Insert a batch of POIs."""
        query = """
            INSERT INTO pois (
                osm_id, geometry, category, subcategory, name,
                address, phone, opening_hours, price_range, website, tags
            )
            VALUES (%s, ST_GeomFromEWKT(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (osm_id) DO UPDATE SET
                geometry = EXCLUDED.geometry,
                category = EXCLUDED.category,
                subcategory = EXCLUDED.subcategory,
                name = EXCLUDED.name,
                address = EXCLUDED.address,
                phone = EXCLUDED.phone,
                opening_hours = EXCLUDED.opening_hours,
                price_range = EXCLUDED.price_range,
                website = EXCLUDED.website,
                tags = EXCLUDED.tags,
                updated_at = NOW()
        """
        async with conn.cursor() as cur:
            await cur.executemany(query, batch)
        await conn.commit()
        return len(batch)

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
                batch.append((
                    zone.osm_id,
                    _coords_to_wkt_polygon(zone.geometry),
                    zone.admin_level.value,
                    zone.name,
                    zone.malagasy_name,
                    zone.iso_code,
                    zone.population,
                    json.dumps(zone.tags) if zone.tags else None,
                ))

                if len(batch) >= self.batch_size:
                    count += await self._insert_zones_batch(conn, batch)
                    batch = []

            if batch:
                count += await self._insert_zones_batch(conn, batch)

        logger.info("Written zones", count=count)
        return count

    async def _insert_zones_batch(
        self,
        conn: AsyncConnection,
        batch: list[tuple[Any, ...]],
    ) -> int:
        """Insert a batch of zones."""
        query = """
            INSERT INTO zones (
                osm_id, geometry, admin_level, name, malagasy_name,
                iso_code, population, tags
            )
            VALUES (%s, ST_GeomFromEWKT(%s), %s, %s, %s, %s, %s, %s)
            ON CONFLICT (osm_id) DO UPDATE SET
                geometry = EXCLUDED.geometry,
                admin_level = EXCLUDED.admin_level,
                name = EXCLUDED.name,
                malagasy_name = EXCLUDED.malagasy_name,
                iso_code = EXCLUDED.iso_code,
                population = EXCLUDED.population,
                tags = EXCLUDED.tags,
                updated_at = NOW()
        """
        async with conn.cursor() as cur:
            await cur.executemany(query, batch)
        await conn.commit()
        return len(batch)
