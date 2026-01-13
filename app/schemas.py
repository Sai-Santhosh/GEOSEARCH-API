"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator


# Generic type for paginated responses
T = TypeVar("T")


class POIBase(BaseModel):
    """Base POI schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="POI name")
    category: str | None = Field(None, max_length=100, description="POI category")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class POICreate(POIBase):
    """Schema for creating a new POI."""
    pass


class POIUpdate(BaseModel):
    """Schema for updating a POI."""
    name: str | None = Field(None, min_length=1, max_length=255)
    category: str | None = Field(None, max_length=100)
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    metadata: dict[str, Any] | None = None


class POIOut(BaseModel):
    """Schema for POI output."""
    id: int = Field(..., description="POI ID")
    name: str = Field(..., description="POI name")
    category: str | None = Field(None, description="POI category")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    dist_m: float | None = Field(None, description="Distance in meters from search point")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    
    model_config = {"from_attributes": True}


class POIOutSimple(BaseModel):
    """Simplified POI output for list views."""
    id: int
    name: str
    category: str | None = None
    lat: float
    lon: float
    dist_m: float | None = None
    
    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int = Field(..., ge=0, description="Total number of items")
    limit: int = Field(..., ge=1, description="Items per page")
    offset: int = Field(..., ge=0, description="Current offset")
    has_more: bool = Field(..., description="Whether more items are available")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: list[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    cached: bool = Field(False, description="Whether response was served from cache")


class NearbyResponse(BaseModel):
    """Response for nearby search."""
    cached: bool = Field(..., description="Whether response was served from cache")
    items: list[POIOutSimple] = Field(..., description="List of POIs")
    count: int = Field(..., description="Number of items returned")
    center: dict[str, float] = Field(..., description="Search center coordinates")
    radius_m: int = Field(..., description="Search radius in meters")


class BBoxResponse(BaseModel):
    """Response for bounding box search."""
    cached: bool = Field(..., description="Whether response was served from cache")
    items: list[POIOutSimple] = Field(..., description="List of POIs")
    count: int = Field(..., description="Number of items returned")
    bounds: dict[str, float] = Field(..., description="Search bounding box")


class SearchResponse(BaseModel):
    """Response for text search."""
    cached: bool = Field(False, description="Whether response was served from cache")
    items: list[POIOutSimple] = Field(..., description="List of POIs")
    count: int = Field(..., description="Number of items returned")
    query: str = Field(..., description="Search query")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Deployment environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class DetailedHealthResponse(HealthResponse):
    """Detailed health check response with component status."""
    components: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Component health status"
    )


class StatsResponse(BaseModel):
    """Statistics response."""
    database: dict[str, Any] = Field(..., description="Database statistics")
    cache: dict[str, Any] = Field(..., description="Cache statistics")
    api: dict[str, Any] = Field(..., description="API statistics")


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")
    request_id: str | None = Field(None, description="Request ID for tracking")


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: dict[str, Any] | None = Field(None, description="Additional data")


class WebSocketMessage(BaseModel):
    """WebSocket message schema."""
    event: str = Field(..., description="Event type")
    data: dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class POIEvent(BaseModel):
    """POI event for real-time updates."""
    event_type: str = Field(..., description="Event type: created, updated, deleted")
    poi: POIOutSimple | None = Field(None, description="POI data (None for deleted)")
    poi_id: int = Field(..., description="POI ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


# Category options for validation
VALID_CATEGORIES = [
    "cafe",
    "restaurant",
    "gas",
    "grocery",
    "park",
    "pharmacy",
    "school",
    "hospital",
    "hotel",
    "bank",
    "atm",
    "parking",
    "transit",
    "attraction",
    "campus",
    "other",
]


class CategoryInfo(BaseModel):
    """Category information."""
    name: str
    count: int = 0


class CategoriesResponse(BaseModel):
    """Categories list response."""
    categories: list[CategoryInfo]
    total: int
