"""
Health check endpoints for monitoring and orchestration.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from .cache import check_cache_health, get_cache_stats
from .db import check_db_health, get_db_stats
from .logging_config import get_logger
from .schemas import HealthResponse, DetailedHealthResponse, StatsResponse
from .settings import settings

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Simple health check for load balancers and basic monitoring.",
)
def health():
    """
    Basic health check endpoint.
    
    Returns 200 OK if the service is running.
    Use /health/ready for dependency checks.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Kubernetes liveness probe - checks if the process is running.",
)
def liveness():
    """
    Liveness probe for Kubernetes.
    
    Returns 200 if the process is alive.
    If this fails, the container should be restarted.
    """
    return HealthResponse(
        status="alive",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/health/ready",
    response_model=DetailedHealthResponse,
    summary="Readiness probe",
    description="Kubernetes readiness probe - checks if all dependencies are available.",
    responses={
        200: {"description": "Service ready"},
        503: {"description": "Service not ready"},
    },
)
def readiness():
    """
    Readiness probe for Kubernetes.
    
    Checks database and cache connectivity.
    Returns 503 if any dependency is unhealthy.
    """
    db_health = check_db_health()
    cache_health = check_cache_health()
    
    components = {
        "database": db_health,
        "cache": cache_health,
    }
    
    # Determine overall status
    all_healthy = all(
        c.get("status") == "healthy"
        for c in components.values()
    )
    
    response = DetailedHealthResponse(
        status="ready" if all_healthy else "not_ready",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
        components=components,
    )
    
    if not all_healthy:
        logger.warning("Readiness check failed", extra={"components": components})
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(mode="json"),
        )
    
    return response


@router.get(
    "/health/stats",
    response_model=StatsResponse,
    summary="System statistics",
    description="Get detailed statistics about database and cache usage.",
    tags=["Monitoring"],
)
def stats():
    """
    Get system statistics.
    
    Returns detailed metrics about database and cache usage.
    Useful for monitoring and debugging.
    """
    from .services import POIService
    from .db import get_db
    
    db_stats = get_db_stats()
    cache_stats = get_cache_stats()
    
    # Get POI stats
    with get_db() as db:
        service = POIService(db)
        poi_stats = service.get_stats()
    
    return StatsResponse(
        database=db_stats,
        cache=cache_stats,
        api={
            "version": settings.app_version,
            "environment": settings.environment,
            "cache_enabled": settings.cache_enabled,
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "rate_limit_enabled": settings.rate_limit_enabled,
            "poi_stats": poi_stats,
        },
    )
