"""
API routes with comprehensive validation and error handling.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session

from .db import get_db_dependency
from .exceptions import GeoSearchException, to_http_exception
from .logging_config import get_logger
from .schemas import (
    NearbyResponse,
    BBoxResponse,
    POIOut,
    POICreate,
    POIUpdate,
    CategoriesResponse,
    SuccessResponse,
    ErrorResponse,
)
from .services import POIService, get_poi_service
from .settings import settings

logger = get_logger(__name__)

router = APIRouter()


# Dependency for POI service
def get_service(db: Session = Depends(get_db_dependency)) -> POIService:
    return get_poi_service(db)


ServiceDep = Annotated[POIService, Depends(get_service)]


# ============================================================================
# Search Endpoints
# ============================================================================

@router.get(
    "/v1/nearby",
    response_model=NearbyResponse,
    summary="Search POIs within radius",
    description="Find points of interest within a specified radius of a geographic point.",
    responses={
        200: {"description": "Successful search"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["Search"],
)
def nearby(
    service: ServiceDep,
    lat: float = Query(
        ...,
        ge=-90,
        le=90,
        description="Latitude of search center",
        examples=[29.7604]
    ),
    lon: float = Query(
        ...,
        ge=-180,
        le=180,
        description="Longitude of search center",
        examples=[-95.3698]
    ),
    radius_m: int = Query(
        default=1000,
        ge=50,
        le=50000,
        description="Search radius in meters",
        examples=[1000, 2000, 5000]
    ),
    category: str | None = Query(
        default=None,
        max_length=100,
        description="Filter by category",
        examples=["cafe", "restaurant", "park"]
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of results"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination"
    ),
):
    """
    Search for POIs within a radius of a geographic point.
    
    The search uses geohash pre-filtering for performance, then
    PostGIS ST_DWithin for precise distance calculation.
    
    Results are sorted by distance from the search center.
    """
    try:
        result = service.nearby_search(
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            category=category,
            limit=limit,
            offset=offset,
        )
        return NearbyResponse(**result)
    except GeoSearchException as e:
        raise to_http_exception(e)


@router.get(
    "/v1/bbox",
    response_model=BBoxResponse,
    summary="Search POIs within bounding box",
    description="Find points of interest within a geographic bounding box.",
    responses={
        200: {"description": "Successful search"},
        400: {"model": ErrorResponse, "description": "Invalid bounds"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["Search"],
)
def bbox(
    service: ServiceDep,
    min_lat: float = Query(
        ...,
        ge=-90,
        le=90,
        description="Minimum latitude (south)",
        examples=[29.73]
    ),
    min_lon: float = Query(
        ...,
        ge=-180,
        le=180,
        description="Minimum longitude (west)",
        examples=[-95.40]
    ),
    max_lat: float = Query(
        ...,
        ge=-90,
        le=90,
        description="Maximum latitude (north)",
        examples=[29.79]
    ),
    max_lon: float = Query(
        ...,
        ge=-180,
        le=180,
        description="Maximum longitude (east)",
        examples=[-95.33]
    ),
    category: str | None = Query(
        default=None,
        max_length=100,
        description="Filter by category"
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of results"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination"
    ),
):
    """
    Search for POIs within a bounding box.
    
    The bounding box is defined by southwest (min) and northeast (max) corners.
    Results are sorted by ID descending (newest first).
    """
    try:
        result = service.bbox_search(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            category=category,
            limit=limit,
            offset=offset,
        )
        return BBoxResponse(**result)
    except GeoSearchException as e:
        raise to_http_exception(e)


# ============================================================================
# POI CRUD Endpoints
# ============================================================================

@router.get(
    "/v1/pois/{poi_id}",
    response_model=POIOut,
    summary="Get POI by ID",
    description="Retrieve a single point of interest by its ID.",
    responses={
        200: {"description": "POI found"},
        404: {"model": ErrorResponse, "description": "POI not found"},
    },
    tags=["POIs"],
)
def get_poi(
    service: ServiceDep,
    poi_id: int = Path(..., ge=1, description="POI ID"),
):
    """Get a single POI by ID."""
    try:
        return service.get_poi(poi_id)
    except GeoSearchException as e:
        raise to_http_exception(e)


@router.post(
    "/v1/pois",
    response_model=POIOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new POI",
    description="Create a new point of interest.",
    responses={
        201: {"description": "POI created"},
        400: {"model": ErrorResponse, "description": "Invalid data"},
    },
    tags=["POIs"],
)
def create_poi(
    service: ServiceDep,
    data: POICreate,
):
    """Create a new POI."""
    try:
        return service.create_poi(data)
    except GeoSearchException as e:
        raise to_http_exception(e)


@router.patch(
    "/v1/pois/{poi_id}",
    response_model=POIOut,
    summary="Update a POI",
    description="Update an existing point of interest.",
    responses={
        200: {"description": "POI updated"},
        404: {"model": ErrorResponse, "description": "POI not found"},
    },
    tags=["POIs"],
)
def update_poi(
    service: ServiceDep,
    data: POIUpdate,
    poi_id: int = Path(..., ge=1, description="POI ID"),
):
    """Update an existing POI."""
    try:
        return service.update_poi(poi_id, data)
    except GeoSearchException as e:
        raise to_http_exception(e)


@router.delete(
    "/v1/pois/{poi_id}",
    response_model=SuccessResponse,
    summary="Delete a POI",
    description="Delete a point of interest.",
    responses={
        200: {"description": "POI deleted"},
        404: {"model": ErrorResponse, "description": "POI not found"},
    },
    tags=["POIs"],
)
def delete_poi(
    service: ServiceDep,
    poi_id: int = Path(..., ge=1, description="POI ID"),
):
    """Delete a POI."""
    try:
        service.delete_poi(poi_id)
        return SuccessResponse(
            success=True,
            message=f"POI {poi_id} deleted successfully"
        )
    except GeoSearchException as e:
        raise to_http_exception(e)


# ============================================================================
# Categories Endpoint
# ============================================================================

@router.get(
    "/v1/categories",
    response_model=CategoriesResponse,
    summary="List categories",
    description="Get all POI categories with counts.",
    tags=["Categories"],
)
def list_categories(service: ServiceDep):
    """Get all categories with their POI counts."""
    try:
        categories = service.get_categories()
        return CategoriesResponse(
            categories=categories,
            total=len(categories)
        )
    except GeoSearchException as e:
        raise to_http_exception(e)
