import geohash2
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import bindparam

from .cache import cache_get, cache_set
from .db import SessionLocal
from .queries import nearby_query, bbox_query
from .schemas import NearbyResponse, BBoxResponse, HealthResponse, POIOut
from .settings import settings

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(ok=True)

def _neighbors_gh5(lat: float, lon: float, precision: int = 5) -> list[str]:
    center = geohash2.encode(lat, lon, precision=precision)
    n = geohash2.neighbors(center)
    return [center] + list(n.values())

@router.get("/v1/nearby", response_model=NearbyResponse)
def nearby(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_m: int = Query(1000, ge=50, le=50000),
    category: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    payload = {
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "radius_m": radius_m,
        "category": category,
        "limit": limit,
        "offset": offset,
    }
    cached = cache_get("nearby", payload)
    if cached is not None:
        return NearbyResponse(cached=True, items=[POIOut(**x) for x in cached["items"]])

    gh5 = _neighbors_gh5(lat, lon, precision=5)
    q = nearby_query.bindparams(bindparam("gh5", expanding=True))

    with SessionLocal() as db:
        rows = db.execute(
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
    cache_set("nearby", payload, {"items": items}, ttl=settings.cache_ttl_seconds)
    return NearbyResponse(cached=False, items=[POIOut(**x) for x in items])

@router.get("/v1/bbox", response_model=BBoxResponse)
def bbox(
    min_lat: float = Query(..., ge=-90, le=90),
    min_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    category: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    if min_lat > max_lat or min_lon > max_lon:
        raise HTTPException(status_code=400, detail="Invalid bbox bounds")

    payload = {
        "min_lat": round(min_lat, 5),
        "min_lon": round(min_lon, 5),
        "max_lat": round(max_lat, 5),
        "max_lon": round(max_lon, 5),
        "category": category,
        "limit": limit,
        "offset": offset,
    }
    cached = cache_get("bbox", payload)
    if cached is not None:
        return BBoxResponse(cached=True, items=[POIOut(**x) for x in cached["items"]])

    with SessionLocal() as db:
        rows = db.execute(
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
    cache_set("bbox", payload, {"items": items}, ttl=settings.cache_ttl_seconds)
    return BBoxResponse(cached=False, items=[POIOut(**x) for x in items])
