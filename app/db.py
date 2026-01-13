"""
Production-grade database configuration with connection pooling and health checks.
"""
import asyncio
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .logging_config import get_logger
from .settings import settings

logger = get_logger(__name__)


def make_engine() -> Engine:
    """Create a production-ready database engine with connection pooling."""
    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,  # Enable connection health checks
        future=True,
        echo=settings.debug,
    )
    
    # Register connection event listeners
    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, connection_record):
        logger.debug("New database connection established")
    
    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_conn, connection_record, connection_proxy):
        logger.debug("Connection checked out from pool")
    
    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_conn, connection_record):
        logger.debug("Connection returned to pool")
    
    return engine


# Global engine instance
engine = make_engine()

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()


def get_db_dependency() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    with get_db() as session:
        yield session


# Schema SQL for initialization
SCHEMA_SQL = """
-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create POI table
CREATE TABLE IF NOT EXISTS poi (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    geohash5 TEXT NOT NULL,
    geom GEOGRAPHY(POINT, 4326) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_poi_geom_gist ON poi USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_poi_geohash5 ON poi (geohash5);
CREATE INDEX IF NOT EXISTS idx_poi_category ON poi (category);
CREATE INDEX IF NOT EXISTS idx_poi_created_at ON poi (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_poi_name_trgm ON poi USING GIN (name gin_trgm_ops);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_poi_updated_at ON poi;
CREATE TRIGGER update_poi_updated_at
    BEFORE UPDATE ON poi
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""


def init_db() -> None:
    """Initialize the database schema."""
    logger.info("Initializing database schema...")
    try:
        with engine.begin() as conn:
            # Enable pg_trgm for fuzzy text search
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            conn.execute(text(SCHEMA_SQL))
        logger.info("Database schema initialized successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def check_db_health() -> dict:
    """Check database health and return status."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as health, version() as version"))
            row = result.fetchone()
            pool_status = engine.pool.status()
            
            return {
                "status": "healthy",
                "database": "postgresql",
                "version": row.version if row else "unknown",
                "pool": {
                    "size": engine.pool.size(),
                    "checked_out": engine.pool.checkedout(),
                    "overflow": engine.pool.overflow(),
                    "status": pool_status,
                }
            }
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def get_db_stats() -> dict:
    """Get database statistics."""
    try:
        with engine.connect() as conn:
            # Get table stats
            result = conn.execute(text("""
                SELECT 
                    relname as table_name,
                    n_live_tup as row_count,
                    pg_size_pretty(pg_total_relation_size(relid)) as total_size
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY n_live_tup DESC
            """))
            tables = [dict(row._mapping) for row in result]
            
            # Get index stats
            result = conn.execute(text("""
                SELECT 
                    indexrelname as index_name,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
                LIMIT 10
            """))
            indexes = [dict(row._mapping) for row in result]
            
            return {
                "tables": tables,
                "indexes": indexes,
                "pool": {
                    "size": engine.pool.size(),
                    "checked_out": engine.pool.checkedout(),
                    "overflow": engine.pool.overflow(),
                }
            }
    except SQLAlchemyError as e:
        logger.error(f"Failed to get database stats: {e}")
        return {"error": str(e)}
