"""
Seed the database with synthetic POIs for testing.

Usage:
    python scripts/seed_synthetic.py --count 10000
    
Docker:
    docker compose exec api python scripts/seed_synthetic.py --count 10000
"""
import argparse
import os
import random
import sys
import time
from typing import Generator

import geohash2
from sqlalchemy import create_engine, text

# Categories with realistic distribution
CATEGORIES = {
    "restaurant": 0.20,
    "cafe": 0.15,
    "grocery": 0.10,
    "gas": 0.08,
    "pharmacy": 0.06,
    "bank": 0.05,
    "atm": 0.05,
    "parking": 0.08,
    "park": 0.05,
    "school": 0.04,
    "hospital": 0.02,
    "hotel": 0.04,
    "transit": 0.05,
    "attraction": 0.03,
}

# Name templates by category
NAME_TEMPLATES = {
    "restaurant": ["The {} Kitchen", "{} Grill", "{} Bistro", "{}'s Restaurant", "{} Diner"],
    "cafe": ["{} Coffee", "The {} Cafe", "{} Roasters", "{} Brew", "Cafe {}"],
    "grocery": ["{} Market", "{} Foods", "{} Grocery", "Fresh {}"],
    "gas": ["{} Gas", "{} Fuel", "{} Station", "{} Petrol"],
    "pharmacy": ["{} Pharmacy", "{} Drugs", "{} Health", "{} Care"],
    "bank": ["{} Bank", "{} Financial", "{} Credit Union"],
    "atm": ["{} ATM", "ATM {}"],
    "parking": ["{} Parking", "{} Garage", "{} Lot"],
    "park": ["{} Park", "{} Gardens", "{} Green"],
    "school": ["{} School", "{} Academy", "{} Elementary"],
    "hospital": ["{} Hospital", "{} Medical Center", "{} Health"],
    "hotel": ["{} Hotel", "{} Inn", "{} Suites", "The {} Lodge"],
    "transit": ["{} Station", "{} Stop", "{} Terminal"],
    "attraction": ["{} Museum", "{} Gallery", "The {} Center"],
}

# Name adjectives
ADJECTIVES = [
    "Central", "Downtown", "Uptown", "Main", "First", "Grand", "Royal",
    "Golden", "Silver", "Green", "Blue", "Sunset", "Sunrise", "North",
    "South", "East", "West", "Park", "Lake", "River", "Hill", "Valley",
    "Oak", "Pine", "Maple", "Cedar", "Elm", "Willow", "Rose", "Lily",
]


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


def weighted_choice(choices: dict) -> str:
    """Select a random item based on weights."""
    items = list(choices.keys())
    weights = list(choices.values())
    return random.choices(items, weights=weights, k=1)[0]


def generate_name(category: str) -> str:
    """Generate a realistic POI name for a category."""
    templates = NAME_TEMPLATES.get(category, ["{} Place"])
    template = random.choice(templates)
    adjective = random.choice(ADJECTIVES)
    return template.format(adjective)


def generate_pois(
    count: int,
    center_lat: float,
    center_lon: float,
    spread: float,
) -> Generator[dict, None, None]:
    """Generate synthetic POI data."""
    for i in range(count):
        # Generate location with slight clustering
        if random.random() < 0.3:
            # Cluster near center
            lat = center_lat + random.gauss(0, spread / 3)
            lon = center_lon + random.gauss(0, spread / 3)
        else:
            # Uniform spread
            lat = center_lat + random.uniform(-spread, spread)
            lon = center_lon + random.uniform(-spread, spread)
        
        # Clamp to valid range
        lat = max(-90, min(90, lat))
        lon = max(-180, min(180, lon))
        
        category = weighted_choice(CATEGORIES)
        name = generate_name(category)
        geohash5 = geohash2.encode(lat, lon, precision=5)
        
        # Generate metadata
        metadata = {
            "rating": round(random.uniform(2.5, 5.0), 1),
            "price_level": random.randint(1, 4),
            "generated": True,
        }
        
        yield {
            "name": name,
            "category": category,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "geohash5": geohash5,
            "metadata": str(metadata).replace("'", '"'),
        }
        
        if (i + 1) % 1000 == 0:
            print(f"  Generated {i + 1:,} POIs...")


def main():
    parser = argparse.ArgumentParser(description="Seed database with synthetic POIs")
    parser.add_argument("--database-url", default=None, help="Database URL")
    parser.add_argument("--count", type=int, default=5000, help="Number of POIs to generate")
    parser.add_argument("--center-lat", type=float, default=29.7604, help="Center latitude")
    parser.add_argument("--center-lon", type=float, default=-95.3698, help="Center longitude")
    parser.add_argument("--spread", type=float, default=0.15, help="Geographic spread")
    parser.add_argument("--truncate", action="store_true", help="Truncate table before seeding")
    parser.add_argument("--batch-size", type=int, default=1000, help="Insert batch size")
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.database_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is required (env var or --database-url)")
        sys.exit(1)
    
    print(f"GeoSearch Synthetic Data Seeder")
    print(f"================================")
    print(f"Target: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print(f"Count: {args.count:,}")
    print(f"Center: ({args.center_lat}, {args.center_lon})")
    print(f"Spread: {args.spread}")
    print()
    
    # Create engine
    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    
    # Initialize schema
    print("Initializing schema...")
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))
        
        if args.truncate:
            print("Truncating existing data...")
            conn.execute(text("TRUNCATE poi RESTART IDENTITY;"))
    
    # Generate and insert POIs
    print(f"Generating {args.count:,} POIs...")
    start_time = time.time()
    
    batch = []
    total_inserted = 0
    
    with engine.begin() as conn:
        for poi in generate_pois(args.count, args.center_lat, args.center_lon, args.spread):
            batch.append(poi)
            
            if len(batch) >= args.batch_size:
                conn.execute(text(INSERT_SQL), batch)
                total_inserted += len(batch)
                batch = []
        
        # Insert remaining
        if batch:
            conn.execute(text(INSERT_SQL), batch)
            total_inserted += len(batch)
    
    elapsed = time.time() - start_time
    rate = total_inserted / elapsed if elapsed > 0 else 0
    
    print()
    print(f"Seeding complete!")
    print(f"  Inserted: {total_inserted:,} POIs")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Rate: {rate:,.0f} POIs/sec")


if __name__ == "__main__":
    main()
