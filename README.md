# GeoSearch API (FastAPI + PostGIS + Redis)

A production-style geospatial search API:
- Nearby search (radius) with distance sorting
- Bounding box search
- Redis caching for hot queries
- PostGIS GiST indexes for fast geo filtering
- Locust load tests
- Docker-first local dev

## Quickstart (Docker Compose)

Start:
```bash
docker compose up --build
```

Seed synthetic POIs:
```bash
docker compose exec api python scripts/seed_synthetic.py --count 5000
```

Try:
```bash
curl http://localhost:8000/health
curl "http://localhost:8000/v1/nearby?lat=29.7604&lon=-95.3698&radius_m=1500&limit=10"
curl "http://localhost:8000/v1/bbox?min_lat=29.73&min_lon=-95.40&max_lat=29.79&max_lon=-95.33&limit=50"
```

## Load test (Locust)

Locust is included in `requirements.txt`.

Run:
```bash
locust -f locust/locustfile.py --host http://localhost:8000
```

Open http://localhost:8089

## Notes

- `poi.geom` is `GEOGRAPHY(Point, 4326)` so distances are in meters.
- Nearby queries use a simple **geohash5 neighbor prefilter** + `ST_DWithin` for accurate radius filtering.
- Cache TTL is controlled by `CACHE_TTL_SECONDS`.

## Deploying to AWS (ECS Fargate + ALB)

This repo is ready to containerize and deploy. Typical setup:
1. Push image to ECR
2. Run Postgres on RDS (enable PostGIS)
3. Optional Redis on ElastiCache
4. ECS Fargate service behind an ALB
5. CloudWatch logs for containers

Set env vars in the task definition:
- `DATABASE_URL`
- `REDIS_URL`
- `CACHE_TTL_SECONDS`
