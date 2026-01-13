"""
Pytest configuration and fixtures for GeoSearch API tests.
"""
import os
import pytest
from typing import Generator
from unittest.mock import MagicMock, patch

# Set test environment before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/test_geosearch")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("CACHE_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import get_db_dependency, SCHEMA_SQL
from app.settings import Settings


# Test database URL (uses SQLite for unit tests, PostgreSQL for integration)
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://test:test@localhost:5432/test_geosearch"
)


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        redis_url="redis://localhost:6379/1",
        environment="development",
        cache_enabled=False,
        rate_limit_enabled=False,
        log_level="WARNING",
    )


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        future=True,
    )
    return engine


@pytest.fixture(scope="session")
def setup_database(test_engine):
    """Set up the test database schema."""
    try:
        with test_engine.begin() as conn:
            # Create PostGIS extension and schema
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            conn.execute(text(SCHEMA_SQL))
        yield test_engine
    finally:
        # Cleanup after all tests
        with test_engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS poi CASCADE;"))


@pytest.fixture
def db_session(setup_database) -> Generator[Session, None, None]:
    """Create a test database session with transaction rollback."""
    TestSessionLocal = sessionmaker(
        bind=setup_database,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    """Create a test client with database session override."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db_dependency] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Mock Redis client for unit tests."""
    with patch("app.cache.redis_client") as mock:
        mock.get.return_value = None
        mock.setex.return_value = True
        mock.delete.return_value = 1
        mock.info.return_value = {
            "redis_version": "7.0.0",
            "uptime_in_seconds": 3600,
            "used_memory_human": "10M",
        }
        yield mock


@pytest.fixture
def sample_poi_data() -> dict:
    """Sample POI data for testing."""
    return {
        "name": "Test Cafe",
        "category": "cafe",
        "lat": 29.7604,
        "lon": -95.3698,
        "metadata": {"rating": 4.5, "price_level": 2},
    }


@pytest.fixture
def sample_pois(db_session, sample_poi_data) -> list[dict]:
    """Create sample POIs in the database."""
    import geohash2
    
    pois = []
    categories = ["cafe", "restaurant", "park", "gas", "grocery"]
    
    for i in range(10):
        lat = 29.7604 + (i * 0.001)
        lon = -95.3698 + (i * 0.001)
        category = categories[i % len(categories)]
        geohash5 = geohash2.encode(lat, lon, precision=5)
        
        result = db_session.execute(
            text("""
                INSERT INTO poi (name, category, lat, lon, geohash5, geom, metadata)
                VALUES (
                    :name, :category, :lat, :lon, :geohash5,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    :metadata::jsonb
                )
                RETURNING id, name, category, lat, lon
            """),
            {
                "name": f"Test POI {i}",
                "category": category,
                "lat": lat,
                "lon": lon,
                "geohash5": geohash5,
                "metadata": "{}",
            }
        )
        poi = dict(result.mappings().first())
        pois.append(poi)
    
    db_session.commit()
    return pois


@pytest.fixture
def houston_center() -> tuple[float, float]:
    """Houston, TX coordinates for testing."""
    return (29.7604, -95.3698)


@pytest.fixture
def houston_bbox() -> dict:
    """Houston bounding box for testing."""
    return {
        "min_lat": 29.73,
        "min_lon": -95.40,
        "max_lat": 29.79,
        "max_lon": -95.33,
    }
