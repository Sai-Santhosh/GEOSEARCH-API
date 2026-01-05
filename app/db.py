from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from .settings import settings

def make_engine() -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)

engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS poi (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT,
  lat DOUBLE PRECISION NOT NULL,
  lon DOUBLE PRECISION NOT NULL,
  geohash5 TEXT NOT NULL,
  geom GEOGRAPHY(POINT, 4326) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_poi_geom_gist ON poi USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_poi_geohash5 ON poi (geohash5);
CREATE INDEX IF NOT EXISTS idx_poi_category ON poi (category);
"""

def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))
