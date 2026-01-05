"""Seed the database with synthetic POIs (license-safe).

Example (docker-compose):
  docker compose exec api python scripts/seed_synthetic.py --count 8000
"""

import argparse
import random

import geohash2
from sqlalchemy import create_engine, text

CATS = ["cafe", "restaurant", "gas", "grocery", "park", "pharmacy", "school"]

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

INSERT_SQL = """
INSERT INTO poi (name, category, lat, lon, geohash5, geom)
VALUES (:name, :category, :lat, :lon, :geohash5, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography);
"""

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", default=None)
    p.add_argument("--count", type=int, default=5000)
    p.add_argument("--center-lat", type=float, default=29.7604)
    p.add_argument("--center-lon", type=float, default=-95.3698)
    p.add_argument("--spread", type=float, default=0.12)
    args = p.parse_args()

    import os
    db_url = args.database_url or os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL is required (env var or --database-url).")

    engine = create_engine(db_url, pool_pre_ping=True, future=True)

    rows = []
    for i in range(args.count):
        lat = args.center_lat + random.uniform(-args.spread, args.spread)
        lon = args.center_lon + random.uniform(-args.spread, args.spread)
        cat = random.choice(CATS)
        gh5 = geohash2.encode(lat, lon, precision=5)
        rows.append({"name": f"{cat}-{i}", "category": cat, "lat": lat, "lon": lon, "geohash5": gh5})

    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))
        conn.execute(text("TRUNCATE poi;"))
        conn.execute(text(INSERT_SQL), rows)

    print(f"Seeded {args.count} POIs.")

if __name__ == "__main__":
    main()
