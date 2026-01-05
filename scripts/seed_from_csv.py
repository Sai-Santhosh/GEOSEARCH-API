"""Seed POIs from a CSV file.

CSV columns: name,category,lat,lon
Example:
  docker compose exec api python scripts/seed_from_csv.py --csv /app/scripts/sample_pois.csv --truncate
"""

import argparse
import csv
from pathlib import Path

import geohash2
from sqlalchemy import create_engine, text

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
    p.add_argument("--csv", required=True)
    p.add_argument("--truncate", action="store_true")
    args = p.parse_args()

    import os
    db_url = args.database_url or os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL is required (env var or --database-url).")

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            lat = float(r["lat"]); lon = float(r["lon"])
            rows.append({
                "name": r["name"],
                "category": r.get("category") or None,
                "lat": lat,
                "lon": lon,
                "geohash5": geohash2.encode(lat, lon, precision=5),
            })

    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))
        if args.truncate:
            conn.execute(text("TRUNCATE poi;"))
        conn.execute(text(INSERT_SQL), rows)

    print(f"Inserted {len(rows)} POIs from {csv_path}.")

if __name__ == "__main__":
    main()
