"""
Seed POIs from a CSV file.

CSV columns: name,category,lat,lon

Usage:
    python scripts/seed_from_csv.py --csv data.csv
    
Docker:
    docker compose exec api python scripts/seed_from_csv.py --csv /app/scripts/sample_pois.csv --truncate
"""
import argparse
import csv
import os
import sys
import time
from pathlib import Path

import geohash2
from sqlalchemy import create_engine, text


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

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

CREATE INDEX IF NOT EXISTS idx_poi_geom_gist ON poi USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_poi_geohash5 ON poi (geohash5);
CREATE INDEX IF NOT EXISTS idx_poi_category ON poi (category);
CREATE INDEX IF NOT EXISTS idx_poi_created_at ON poi (created_at DESC);
"""

INSERT_SQL = """
INSERT INTO poi (name, category, lat, lon, geohash5, geom, metadata)
VALUES (
    :name, :category, :lat, :lon, :geohash5,
    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
    :metadata::jsonb
);
"""


def main():
    parser = argparse.ArgumentParser(description="Seed POIs from CSV file")
    parser.add_argument("--database-url", default=None, help="Database URL")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--truncate", action="store_true", help="Truncate table first")
    parser.add_argument("--batch-size", type=int, default=500, help="Insert batch size")
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.database_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is required (env var or --database-url)")
        sys.exit(1)
    
    # Check CSV file
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)
    
    print(f"GeoSearch CSV Data Importer")
    print(f"===========================")
    print(f"Source: {csv_path}")
    print(f"Target: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print()
    
    # Read CSV
    print("Reading CSV file...")
    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                lat = float(r["lat"])
                lon = float(r["lon"])
                
                # Validate coordinates
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    print(f"  WARNING: Invalid coordinates for '{r.get('name', 'unknown')}': ({lat}, {lon})")
                    continue
                
                rows.append({
                    "name": r["name"].strip(),
                    "category": r.get("category", "").strip() or None,
                    "lat": lat,
                    "lon": lon,
                    "geohash5": geohash2.encode(lat, lon, precision=5),
                    "metadata": "{}",
                })
            except (ValueError, KeyError) as e:
                print(f"  WARNING: Skipping invalid row: {e}")
                continue
    
    print(f"  Found {len(rows)} valid POIs")
    print()
    
    if not rows:
        print("No valid POIs to import.")
        sys.exit(0)
    
    # Create engine
    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    
    # Initialize schema and insert
    print("Initializing schema...")
    start_time = time.time()
    
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))
        
        if args.truncate:
            print("Truncating existing data...")
            conn.execute(text("TRUNCATE poi RESTART IDENTITY;"))
        
        # Insert in batches
        print(f"Inserting {len(rows)} POIs...")
        total_inserted = 0
        
        for i in range(0, len(rows), args.batch_size):
            batch = rows[i:i + args.batch_size]
            conn.execute(text(INSERT_SQL), batch)
            total_inserted += len(batch)
            print(f"  Inserted {total_inserted}/{len(rows)} POIs...")
    
    elapsed = time.time() - start_time
    rate = total_inserted / elapsed if elapsed > 0 else 0
    
    print()
    print(f"Import complete!")
    print(f"  Inserted: {total_inserted:,} POIs")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Rate: {rate:,.0f} POIs/sec")


if __name__ == "__main__":
    main()
