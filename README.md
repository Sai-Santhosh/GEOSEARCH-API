# GeoSearch API

A geospatial search backend built with **FastAPI + PostgreSQL/PostGIS + Redis**, designed to feel like a real production service: clean REST endpoints, fast geo queries, caching, and repeatable load testing.

It supports:
- **Nearby search (radius)** with distance sorting
- **Bounding-box search**
- **Category filtering + pagination**
- **Redis caching** for hot queries
- **PostGIS indexing** for fast geo filtering
- **Seed scripts** (synthetic + CSV)
- **Locust load tests**
- **Docker-first local dev**

---

## Architecture

```
Client
  └── HTTP (REST)
        └── FastAPI (GeoSearch API)
              ├── Redis (cache: hot queries)
              └── Postgres + PostGIS (POI storage + geo indexes)
```

### How queries stay fast
- **Geohash prefilter (precision=5)** reduces the candidate set for radius queries.
- **PostGIS GiST index** accelerates `ST_DWithin` filtering.
- **Redis cache** stores responses for repeated queries (TTL-based) to avoid repeated DB work.

---

## Data Model

Table: `poi`

| Column     | Type                        | Notes |
|-----------|-----------------------------|------|
| id        | BIGSERIAL (PK)              | |
| name      | TEXT                        | required |
| category  | TEXT                        | optional |
| lat       | DOUBLE PRECISION            | required |
| lon       | DOUBLE PRECISION            | required |
| geohash5  | TEXT                        | used for candidate blocking |
| geom      | GEOGRAPHY(POINT, 4326)      | PostGIS geography point |
| created_at| TIMESTAMPTZ                 | default NOW() |

Indexes:
- `geom` GiST index (geo filtering)
- `geohash5` btree index (prefilter for nearby)
- `category` btree index (optional filter)

---

## API Endpoints

### Health
**GET** `/health`

Response:
```json
{ "ok": true, "version": "1.0.0" }
```

### Nearby (radius search)
**GET** `/v1/nearby`

Query params:
- `lat` (float, required)
- `lon` (float, required)
- `radius_m` (int, default 1000, range 50–50000)
- `category` (string, optional)
- `limit` (int, default 50, max 200)
- `offset` (int, default 0)

Response:
```json
{
  "cached": false,
  "items": [
    { "id": 12, "name": "cafe-42", "category": "cafe", "lat": 29.76, "lon": -95.36, "dist_m": 184.3 }
  ]
}
```

Example:
```bash
curl "http://localhost:8000/v1/nearby?lat=29.7604&lon=-95.3698&radius_m=1500&limit=10"
```

### Bounding box search
**GET** `/v1/bbox`

Query params:
- `min_lat` (float, required)
- `min_lon` (float, required)
- `max_lat` (float, required)
- `max_lon` (float, required)
- `category` (string, optional)
- `limit` (int, default 100, max 500)
- `offset` (int, default 0)

Example:
```bash
curl "http://localhost:8000/v1/bbox?min_lat=29.73&min_lon=-95.40&max_lat=29.79&max_lon=-95.33&limit=50"
```

---

## Quickstart (Docker Compose)

### 1) Start services
```bash
docker compose up --build
```

API will be available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **Health:** `http://localhost:8000/health`

### 2) Seed data (recommended)
Synthetic POIs (license-safe):
```bash
docker compose exec api python scripts/seed_synthetic.py --count 8000
```

Seed from the included CSV:
```bash
docker compose exec api python scripts/seed_from_csv.py --csv scripts/sample_pois.csv --truncate
```

### 3) Test a request
```bash
curl "http://localhost:8000/v1/nearby?lat=29.7604&lon=-95.3698&radius_m=1500&limit=10"
```

---

## Configuration

This service reads environment variables (see `.env.example`):

- `DATABASE_URL`  
  Example:
  `postgresql+psycopg2://geosearch:geosearch@db:5432/geosearch`
- `REDIS_URL`  
  Example:
  `redis://redis:6379/0`
- `CACHE_TTL_SECONDS` (default `60`)

Docker Compose sets these automatically for local development.

---

## Caching Behavior

- The API caches responses for `/v1/nearby` and `/v1/bbox`.
- Cache keys are stable-hashed from request parameters.
- Lat/lon are rounded to improve cache hit rate for near-identical queries.
- Cache is TTL-based (no manual invalidation by default).

If you want “instant freshness,” set `CACHE_TTL_SECONDS=0` (or remove caching calls).

---

## Load Testing (Locust)

A basic Locust workload is included in `locust/locustfile.py`.

### Run Locust locally
If your API is running at `http://localhost:8000`:
```bash
locust -f locust/locustfile.py --host http://localhost:8000
```

Then open:
- `http://localhost:8089`

This workload mixes:
- `/v1/nearby` (most traffic)
- `/v1/bbox` (some traffic)

Use this to compare p95 latency with/without caching, different dataset sizes, or different indexes.

---

## Local Development (without Docker)

You can run the API directly if you have:
- Postgres with PostGIS enabled
- Redis

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+psycopg2://USER:PASS@HOST:5432/geosearch"
export REDIS_URL="redis://localhost:6379/0"
export CACHE_TTL_SECONDS=60

uvicorn app.main:app --reload
```

Then seed:
```bash
python scripts/seed_synthetic.py --count 5000 --database-url "$DATABASE_URL"
```

---

## Deploying to AWS (ECS Fargate)

This repo is structured to deploy cleanly to AWS:
- **ECS Fargate** for running the container
- **ALB** for routing traffic + health checks
- **CloudWatch Logs** for container logs
- **RDS Postgres** (enable PostGIS) for the database
- **ElastiCache Redis** (optional) for caching

Minimum environment variables in ECS task definition:
- `DATABASE_URL`
- `REDIS_URL`
- `CACHE_TTL_SECONDS`

Operational notes:
- Use ALB health check path: `/health`
- Set autoscaling based on CPU or request count if desired
- Store secrets in AWS Secrets Manager or SSM Parameter Store (recommended)

---

## Security Notes (for production use)

This project intentionally ships “simple by default.” If you deploy publicly, you should add:
- Authentication (JWT / OAuth) or private networking (VPC-only)
- Rate limiting / request throttling
- Input allowlists for category values (if needed)
- Audit logging + request IDs
- More robust caching invalidation strategy (if data changes frequently)

---

## Project Layout

```
app/
  main.py        # FastAPI app bootstrap
  routes.py      # HTTP routes + request handling
  queries.py     # SQL queries (nearby + bbox)
  db.py          # engine/session + schema init
  cache.py       # Redis cache utilities
  schemas.py     # Pydantic response models
scripts/
  seed_synthetic.py  # license-safe synthetic seeding
  seed_from_csv.py   # seed from CSV
  sample_pois.csv    # example dataset
locust/
  locustfile.py      # load test workload
```

---

## License

Add a `LICENSE` file if you plan to open-source this publicly (MIT is common for projects like this).

---

## Attribution / Data Sources

- The repo includes **synthetic seeding** and a tiny sample CSV so you can run it immediately.
- If you swap in a public POI dataset, make sure you follow its license/attribution rules.
