"""
Custom exceptions and error handling for the GeoSearch API.
"""
from typing import Any

from fastapi import HTTPException, status


class GeoSearchException(Exception):
    """Base exception for GeoSearch API."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(GeoSearchException):
    """Validation error for invalid input."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details
        )


class InvalidBoundsError(ValidationError):
    """Invalid geographic bounds."""
    
    def __init__(self, message: str = "Invalid geographic bounds"):
        super().__init__(message=message, details={"field": "bounds"})


class InvalidCoordinatesError(ValidationError):
    """Invalid coordinates."""
    
    def __init__(self, lat: float | None = None, lon: float | None = None):
        details = {}
        if lat is not None:
            details["lat"] = lat
        if lon is not None:
            details["lon"] = lon
        super().__init__(
            message="Invalid coordinates provided",
            details=details
        )


class RadiusOutOfRangeError(ValidationError):
    """Radius outside allowed range."""
    
    def __init__(self, radius: int, min_radius: int = 50, max_radius: int = 50000):
        super().__init__(
            message=f"Radius must be between {min_radius}m and {max_radius}m",
            details={"radius": radius, "min": min_radius, "max": max_radius}
        )


class DatabaseError(GeoSearchException):
    """Database connection or query error."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="DATABASE_ERROR"
        )


class CacheError(GeoSearchException):
    """Cache operation error."""
    
    def __init__(self, message: str = "Cache operation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="CACHE_ERROR"
        )


class RateLimitExceeded(GeoSearchException):
    """Rate limit exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )


class NotFoundError(GeoSearchException):
    """Resource not found."""
    
    def __init__(self, resource: str = "Resource", resource_id: Any = None):
        details = {"resource": resource}
        if resource_id is not None:
            details["id"] = resource_id
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details
        )


class POINotFoundError(NotFoundError):
    """POI not found."""
    
    def __init__(self, poi_id: int):
        super().__init__(resource="POI", resource_id=poi_id)


class AuthenticationError(GeoSearchException):
    """Authentication failed."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(GeoSearchException):
    """Authorization failed."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR"
        )


def to_http_exception(exc: GeoSearchException) -> HTTPException:
    """Convert GeoSearchException to FastAPI HTTPException."""
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )
