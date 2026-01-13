"""
Business logic services for POI operations.
"""
from datetime import datetime
from typing import Any

import geohash2
import orjson
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from .cache import cache_delete, cache_get, cache_set, cache_clear_prefix, pubsub
from .db import get_db
from .exceptions import POINotFoundError, ValidationError
from .logging_config import get_logger
from .queries import (
    nearby_query,
    bbox_query,
    get_poi_query,
    insert_poi_query,
    update_poi_query,
    delete_poi_query,
    categories_query,
    poi_stats_query,
    bulk_insert_query,
)
from .schemas import POICreate, POIUpdate, POIOut, POIOutSimple, CategoryInfo
from .settings import settings

logger = get_logger(__name__)


def get_neighbors_geohash(lat: float, lon: float, precision: int = 5) -> list[str]:
    """Get center geohash and all neighbors for pre-filtering."""
    center = geohash2.encode(lat, lon, precision=precision)
    neighbors = geohash2.neighbors(center)
    return [center] + list(neighbors.values())


class POIService:
    """Service for POI operations with caching and validation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def nearby_search(
        self,
        lat: float,
        lon: float,
        radius_m: int = 1000,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Search for POIs within a radius of a point.
        Uses geohash pre-filtering for performance.
        """
        # Build cache key
        cache_payload = {
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "radius_m": radius_m,
            "category": category,
            "limit": limit,
            "offset": offset,
        }
        
        # Check cache
        cached = cache_get("nearby", cache_payload)
        if cached is not None:
            logger.debug(f"Cache hit for nearby search at ({lat}, {lon})")
            return {
                "cached": True,
                "items": [POIOutSimple(**x) for x in cached["items"]],
                "count": cached["count"],
                "center": {"lat": lat, "lon": lon},
                "radius_m": radius_m,
            }
        
        # Get geohash neighbors for pre-filtering
        gh5 = get_neighbors_geohash(lat, lon, precision=settings.geohash_precision)
        
        # Execute query
        q = nearby_query.bindparams(bindparam("gh5", expanding=True))
        rows = self.db.execute(
            q,
            {
                "lat": lat,
                "lon": lon,
                "radius_m": radius_m,
                "category": category,
                "limit": limit,
                "offset": offset,
                "gh5": gh5,
            },
        ).mappings().all()
        
        items = [dict(r) for r in rows]
        
        # Cache result
        cache_set(
            "nearby",
            cache_payload,
            {"items": items, "count": len(items)},
            ttl=settings.cache_ttl_seconds
        )
        
        return {
            "cached": False,
            "items": [POIOutSimple(**x) for x in items],
            "count": len(items),
            "center": {"lat": lat, "lon": lon},
            "radius_m": radius_m,
        }
    
    def bbox_search(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Search for POIs within a bounding box.
        """
        # Validate bounds
        if min_lat > max_lat or min_lon > max_lon:
            raise ValidationError("Invalid bounding box: min values must be less than max values")
        
        # Build cache key
        cache_payload = {
            "min_lat": round(min_lat, 5),
            "min_lon": round(min_lon, 5),
            "max_lat": round(max_lat, 5),
            "max_lon": round(max_lon, 5),
            "category": category,
            "limit": limit,
            "offset": offset,
        }
        
        # Check cache
        cached = cache_get("bbox", cache_payload)
        if cached is not None:
            logger.debug(f"Cache hit for bbox search")
            return {
                "cached": True,
                "items": [POIOutSimple(**x) for x in cached["items"]],
                "count": cached["count"],
                "bounds": {
                    "min_lat": min_lat,
                    "min_lon": min_lon,
                    "max_lat": max_lat,
                    "max_lon": max_lon,
                },
            }
        
        # Execute query
        rows = self.db.execute(
            bbox_query,
            {
                "min_lat": min_lat,
                "min_lon": min_lon,
                "max_lat": max_lat,
                "max_lon": max_lon,
                "category": category,
                "limit": limit,
                "offset": offset,
            },
        ).mappings().all()
        
        items = [dict(r) for r in rows]
        
        # Cache result
        cache_set(
            "bbox",
            cache_payload,
            {"items": items, "count": len(items)},
            ttl=settings.cache_ttl_seconds
        )
        
        return {
            "cached": False,
            "items": [POIOutSimple(**x) for x in items],
            "count": len(items),
            "bounds": {
                "min_lat": min_lat,
                "min_lon": min_lon,
                "max_lat": max_lat,
                "max_lon": max_lon,
            },
        }
    
    def get_poi(self, poi_id: int) -> POIOut:
        """Get a single POI by ID."""
        # Check cache
        cached = cache_get("poi", {"id": poi_id})
        if cached is not None:
            return POIOut(**cached)
        
        # Query database
        row = self.db.execute(get_poi_query, {"id": poi_id}).mappings().first()
        
        if row is None:
            raise POINotFoundError(poi_id)
        
        poi_data = dict(row)
        
        # Cache result
        cache_set("poi", {"id": poi_id}, poi_data, ttl=settings.cache_ttl_seconds)
        
        return POIOut(**poi_data)
    
    def create_poi(self, data: POICreate) -> POIOut:
        """Create a new POI."""
        # Calculate geohash
        geohash5 = geohash2.encode(data.lat, data.lon, precision=settings.geohash_precision)
        
        # Prepare metadata
        metadata_json = orjson.dumps(data.metadata).decode("utf-8") if data.metadata else "{}"
        
        # Insert POI
        row = self.db.execute(
            insert_poi_query,
            {
                "name": data.name,
                "category": data.category,
                "lat": data.lat,
                "lon": data.lon,
                "geohash5": geohash5,
                "metadata": metadata_json,
            },
        ).mappings().first()
        
        self.db.commit()
        
        poi_data = dict(row)
        poi = POIOut(**poi_data)
        
        # Invalidate nearby caches
        cache_clear_prefix("nearby")
        cache_clear_prefix("bbox")
        
        # Publish event
        pubsub.publish("poi", {
            "event_type": "created",
            "poi_id": poi.id,
            "poi": poi_data,
        })
        
        logger.info(f"Created POI {poi.id}: {poi.name}")
        return poi
    
    def update_poi(self, poi_id: int, data: POIUpdate) -> POIOut:
        """Update an existing POI."""
        # Check if POI exists
        existing = self.db.execute(get_poi_query, {"id": poi_id}).mappings().first()
        if existing is None:
            raise POINotFoundError(poi_id)
        
        # Calculate new geohash if coordinates changed
        geohash5 = None
        if data.lat is not None or data.lon is not None:
            lat = data.lat if data.lat is not None else existing["lat"]
            lon = data.lon if data.lon is not None else existing["lon"]
            geohash5 = geohash2.encode(lat, lon, precision=settings.geohash_precision)
        
        # Prepare metadata
        metadata_json = None
        if data.metadata is not None:
            metadata_json = orjson.dumps(data.metadata).decode("utf-8")
        
        # Update POI
        row = self.db.execute(
            update_poi_query,
            {
                "id": poi_id,
                "name": data.name,
                "category": data.category,
                "lat": data.lat,
                "lon": data.lon,
                "geohash5": geohash5,
                "metadata": metadata_json,
            },
        ).mappings().first()
        
        self.db.commit()
        
        poi_data = dict(row)
        poi = POIOut(**poi_data)
        
        # Invalidate caches
        cache_delete("poi", {"id": poi_id})
        cache_clear_prefix("nearby")
        cache_clear_prefix("bbox")
        
        # Publish event
        pubsub.publish("poi", {
            "event_type": "updated",
            "poi_id": poi.id,
            "poi": poi_data,
        })
        
        logger.info(f"Updated POI {poi.id}: {poi.name}")
        return poi
    
    def delete_poi(self, poi_id: int) -> bool:
        """Delete a POI."""
        # Check if POI exists
        existing = self.db.execute(get_poi_query, {"id": poi_id}).mappings().first()
        if existing is None:
            raise POINotFoundError(poi_id)
        
        # Delete POI
        self.db.execute(delete_poi_query, {"id": poi_id})
        self.db.commit()
        
        # Invalidate caches
        cache_delete("poi", {"id": poi_id})
        cache_clear_prefix("nearby")
        cache_clear_prefix("bbox")
        
        # Publish event
        pubsub.publish("poi", {
            "event_type": "deleted",
            "poi_id": poi_id,
            "poi": None,
        })
        
        logger.info(f"Deleted POI {poi_id}")
        return True
    
    def get_categories(self) -> list[CategoryInfo]:
        """Get all categories with counts."""
        # Check cache
        cached = cache_get("categories", {})
        if cached is not None:
            return [CategoryInfo(**c) for c in cached]
        
        # Query database
        rows = self.db.execute(categories_query).mappings().all()
        
        categories = [
            {"name": row["category"], "count": row["count"]}
            for row in rows
        ]
        
        # Cache result
        cache_set("categories", {}, categories, ttl=settings.cache_ttl_seconds * 10)
        
        return [CategoryInfo(**c) for c in categories]
    
    def get_stats(self) -> dict[str, Any]:
        """Get POI statistics."""
        row = self.db.execute(poi_stats_query).mappings().first()
        
        if row is None:
            return {
                "total_pois": 0,
                "category_count": 0,
                "bounds": None,
            }
        
        return {
            "total_pois": row["total_pois"],
            "category_count": row["category_count"],
            "oldest_poi": row["oldest_poi"],
            "newest_poi": row["newest_poi"],
            "bounds": {
                "min_lat": row["min_lat"],
                "min_lon": row["min_lon"],
                "max_lat": row["max_lat"],
                "max_lon": row["max_lon"],
            } if row["min_lat"] is not None else None,
        }
    
    def bulk_create(self, pois: list[POICreate]) -> int:
        """Bulk create POIs."""
        if not pois:
            return 0
        
        rows = []
        for poi in pois:
            geohash5 = geohash2.encode(poi.lat, poi.lon, precision=settings.geohash_precision)
            metadata_json = orjson.dumps(poi.metadata).decode("utf-8") if poi.metadata else "{}"
            rows.append({
                "name": poi.name,
                "category": poi.category,
                "lat": poi.lat,
                "lon": poi.lon,
                "geohash5": geohash5,
                "metadata": metadata_json,
            })
        
        self.db.execute(bulk_insert_query, rows)
        self.db.commit()
        
        # Invalidate caches
        cache_clear_prefix("nearby")
        cache_clear_prefix("bbox")
        cache_clear_prefix("categories")
        
        logger.info(f"Bulk created {len(rows)} POIs")
        return len(rows)


def get_poi_service(db: Session) -> POIService:
    """Factory function for POIService."""
    return POIService(db)
