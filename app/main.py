"""
GeoSearch API - Production-grade geospatial search service.

A high-performance geospatial search API built with FastAPI, PostGIS, and Redis.
Supports nearby radius search, bounding box queries, real-time WebSocket updates,
and comprehensive caching for optimal performance.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import init_db
from .exceptions import GeoSearchException
from .health import router as health_router
from .logging_config import get_logger, setup_logging
from .middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from .routes import router as api_router
from .settings import settings
from .websocket import router as ws_router

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info(
        f"Starting GeoSearch API v{settings.app_version} "
        f"in {settings.environment} mode"
    )
    
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    logger.info(f"GeoSearch API ready at http://{settings.host}:{settings.port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GeoSearch API")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## GeoSearch API

A high-performance geospatial search API for points of interest (POI).

### Features

- **Nearby Search**: Find POIs within a radius of a geographic point
- **Bounding Box Search**: Find POIs within a rectangular area
- **Real-time Updates**: WebSocket support for live POI updates
- **High Performance**: PostGIS spatial indexing + Redis caching
- **Production Ready**: Health checks, rate limiting, structured logging

### Authentication

API key authentication can be enabled via the `API_KEY_ENABLED` environment variable.
When enabled, include your API key in the `X-API-Key` header.

### Rate Limiting

Rate limiting is enabled by default. Limits are per-client based on IP address
or API key. Check the `X-RateLimit-*` headers in responses for limit information.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=settings.debug,
)

# Add middleware (order matters - first added = outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-Response-Time",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)

if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window,
    )


# Exception handlers
@app.exception_handler(GeoSearchException)
async def geosearch_exception_handler(request: Request, exc: GeoSearchException):
    """Handle custom GeoSearch exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        f"GeoSearch error: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "request_id": request_id,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    request_id = getattr(request.state, "request_id", None)
    
    # Extract meaningful error details
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(
        f"Validation error: {len(errors)} errors",
        extra={"errors": errors, "request_id": request_id}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": errors},
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    logger.exception(
        f"Unexpected error: {exc}",
        extra={"request_id": request_id}
    )
    
    # Don't expose internal errors in production
    message = str(exc) if settings.debug else "An unexpected error occurred"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": message,
            "request_id": request_id,
        },
    )


# Include routers
app.include_router(health_router)
app.include_router(api_router)
app.include_router(ws_router)


# Root endpoint
@app.get("/", include_in_schema=False)
def root():
    """Redirect to API documentation."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "api": "/v1/nearby",
    }
