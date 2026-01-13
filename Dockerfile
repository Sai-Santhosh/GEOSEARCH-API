# ============================================================================
# GeoSearch API - Production Dockerfile
# ============================================================================
# Multi-stage build for minimal production image

# Build stage
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# Production stage
FROM python:3.11-slim as production

# Labels
LABEL org.opencontainers.image.title="GeoSearch API" \
      org.opencontainers.image.description="High-performance geospatial search API" \
      org.opencontainers.image.vendor="GeoSearch" \
      org.opencontainers.image.source="https://github.com/yourusername/geosearch-api"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # Application defaults
    HOST=0.0.0.0 \
    PORT=8000 \
    WORKERS=1 \
    ENVIRONMENT=production \
    LOG_FORMAT=json

# Create non-root user for security
RUN groupadd --gid 1000 geosearch && \
    useradd --uid 1000 --gid geosearch --shell /bin/bash --create-home geosearch

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY --chown=geosearch:geosearch app ./app
COPY --chown=geosearch:geosearch scripts ./scripts
COPY --chown=geosearch:geosearch locust ./locust

# Switch to non-root user
USER geosearch

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run application
CMD ["sh", "-c", "uvicorn app.main:app --host $HOST --port $PORT --workers $WORKERS"]
