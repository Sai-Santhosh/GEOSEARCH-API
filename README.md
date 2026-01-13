<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-PostGIS-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-7.0+-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
</p>

<h1 align="center">🌍 GeoSearch API</h1>

<p align="center">
  <strong>A high-performance, production-ready geospatial search API</strong><br>
  Built with FastAPI, PostGIS, and Redis for lightning-fast location queries
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-api-reference">API Reference</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-deployment">Deployment</a> •
  <a href="#-testing">Testing</a>
</p>

---

## ✨ Features

### Core Capabilities
- **🔍 Nearby Search** - Find POIs within a radius with distance sorting
- **📦 Bounding Box Search** - Query POIs within rectangular areas
- **🏷️ Category Filtering** - Filter results by POI categories
- **📄 Pagination** - Efficient pagination for large result sets
- **⚡ Real-time Updates** - WebSocket support for live POI changes

### Performance
- **🚀 PostGIS Indexing** - GiST spatial indexes for sub-millisecond queries
- **📊 Geohash Pre-filtering** - Reduces candidate sets for radius queries
- **💾 Redis Caching** - Hot query caching with configurable TTL
- **🔄 Connection Pooling** - Efficient database connection management

### Production Ready
- **🔒 Security** - Rate limiting, CORS, security headers, API key auth
- **📈 Observability** - Structured JSON logging, health checks, metrics
- **🐳 Docker** - Multi-stage builds, health checks, non-root user
- **🧪 Testing** - Comprehensive unit and integration test suite
- **🔄 CI/CD** - GitHub Actions for testing, building, and deployment

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- (Optional) Python 3.11+ for local development

### 1. Clone and Start

```bash
git clone https://github.com/yourusername/geosearch-api.git
cd geosearch-api

# Start all services
docker compose up --build
```

### 2. Seed Sample Data

```bash
# Generate 10,000 synthetic POIs around Houston, TX
docker compose exec api python scripts/seed_synthetic.py --count 10000
```

### 3. Try It Out

```bash
# Health check
curl http://localhost:8000/health

# Nearby search
curl "http://localhost:8000/v1/nearby?lat=29.7604&lon=-95.3698&radius_m=2000"

# Bounding box search
curl "http://localhost:8000/v1/bbox?min_lat=29.73&min_lon=-95.40&max_lat=29.79&max_lon=-95.33"
```

### 4. Explore the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/health

---

## 📚 API Reference

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Basic health check |
| `GET /health/live` | Kubernetes liveness probe |
| `GET /health/ready` | Kubernetes readiness probe with dependency checks |
| `GET /health/stats` | Detailed system statistics |

### Search Endpoints

#### Nearby Search
```http
GET /v1/nearby?lat={lat}&lon={lon}&radius_m={radius}&category={cat}&limit={n}&offset={n}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `lat` | float | ✅ | - | Latitude (-90 to 90) |
| `lon` | float | ✅ | - | Longitude (-180 to 180) |
| `radius_m` | int | ❌ | 1000 | Search radius in meters (50-50000) |
| `category` | string | ❌ | - | Filter by category |
| `limit` | int | ❌ | 50 | Max results (1-200) |
| `offset` | int | ❌ | 0 | Pagination offset |

**Response:**
```json
{
  "cached": false,
  "count": 25,
  "center": {"lat": 29.7604, "lon": -95.3698},
  "radius_m": 2000,
  "items": [
    {
      "id": 1234,
      "name": "Central Coffee",
      "category": "cafe",
      "lat": 29.7610,
      "lon": -95.3695,
      "dist_m": 72.5
    }
  ]
}
```

#### Bounding Box Search
```http
GET /v1/bbox?min_lat={}&min_lon={}&max_lat={}&max_lon={}&category={}&limit={}&offset={}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `min_lat` | float | ✅ | South boundary |
| `min_lon` | float | ✅ | West boundary |
| `max_lat` | float | ✅ | North boundary |
| `max_lon` | float | ✅ | East boundary |
| `category` | string | ❌ | Filter by category |
| `limit` | int | ❌ | Max results (1-500) |
| `offset` | int | ❌ | Pagination offset |

### POI CRUD Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/pois/{id}` | Get POI by ID |
| `POST` | `/v1/pois` | Create new POI |
| `PATCH` | `/v1/pois/{id}` | Update POI |
| `DELETE` | `/v1/pois/{id}` | Delete POI |
| `GET` | `/v1/categories` | List all categories |

**Create POI Example:**
```bash
curl -X POST http://localhost:8000/v1/pois \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Coffee Shop",
    "category": "cafe",
    "lat": 29.7604,
    "lon": -95.3698,
    "metadata": {"phone": "+1-555-1234"}
  }'
```

### WebSocket

Connect to `/ws` for real-time POI updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  // Subscribe to POI events
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'poi' }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('POI event:', data);
  // { type: 'poi_created', poi_id: 123, data: {...} }
};
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                  │
│              (Web, Mobile, IoT, Third-party)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Load Balancer / CDN                          │
│                   (AWS ALB, CloudFlare)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GeoSearch API                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FastAPI Application                                      │   │
│  │  ├── Middleware (CORS, Rate Limit, Security, Logging)    │   │
│  │  ├── Routes (v1/nearby, v1/bbox, v1/pois)               │   │
│  │  ├── Services (POIService with business logic)          │   │
│  │  └── WebSocket (Real-time updates)                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                    │                       │
                    ▼                       ▼
┌────────────────────────────┐  ┌────────────────────────────────┐
│       PostgreSQL           │  │          Redis                  │
│       + PostGIS            │  │                                 │
│  ┌──────────────────────┐  │  │  ┌────────────────────────┐    │
│  │ POI Table            │  │  │  │ Query Cache            │    │
│  │ ├── GiST Index       │  │  │  │ (nearby:*, bbox:*)    │    │
│  │ ├── Geohash Index    │  │  │  ├────────────────────────┤    │
│  │ └── Category Index   │  │  │  │ Pub/Sub Channels      │    │
│  └──────────────────────┘  │  │  │ (poi events)          │    │
└────────────────────────────┘  │  └────────────────────────┘    │
                                └────────────────────────────────┘
```

### Query Performance Optimization

1. **Geohash Pre-filtering**: Nearby queries first filter by geohash5 neighbors, reducing the candidate set by ~90%

2. **PostGIS ST_DWithin**: Final distance filtering uses PostGIS's optimized spatial function

3. **Redis Caching**: Repeated queries hit cache with stable keys based on rounded coordinates

4. **Connection Pooling**: SQLAlchemy pool with health checks and recycling

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *required* | PostgreSQL connection URL |
| `REDIS_URL` | *required* | Redis connection URL |
| `ENVIRONMENT` | development | Environment: development, staging, production |
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_FORMAT` | json | Log format: json or text |
| `CACHE_ENABLED` | true | Enable Redis caching |
| `CACHE_TTL_SECONDS` | 60 | Cache TTL |
| `RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | 100 | Requests per window |
| `RATE_LIMIT_WINDOW` | 60 | Rate limit window (seconds) |
| `CORS_ORIGINS` | * | Allowed CORS origins |
| `API_KEY_ENABLED` | false | Enable API key authentication |
| `API_KEYS` | - | Comma-separated API keys |

### Example `.env` File

```env
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/geosearch
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
LOG_LEVEL=INFO
CACHE_TTL_SECONDS=60
RATE_LIMIT_ENABLED=true
```

---

## 🐳 Deployment

### Docker Compose (Development)

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api

# Seed data
docker compose exec api python scripts/seed_synthetic.py --count 10000

# Run load tests
docker compose --profile testing up locust
```

### Production Deployment

#### AWS ECS Fargate

1. **Build and push image:**
```bash
docker build -t ghcr.io/yourusername/geosearch-api:latest .
docker push ghcr.io/yourusername/geosearch-api:latest
```

2. **Create ECS Task Definition** with environment variables:
   - `DATABASE_URL` (use Secrets Manager)
   - `REDIS_URL` (ElastiCache endpoint)
   - `ENVIRONMENT=production`

3. **Configure ALB** with health check path `/health`

4. **Set up auto-scaling** based on CPU or request count

#### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: geosearch-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: geosearch-api
  template:
    metadata:
      labels:
        app: geosearch-api
    spec:
      containers:
      - name: api
        image: ghcr.io/yourusername/geosearch-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: geosearch-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: geosearch-secrets
              key: redis-url
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

---

## 🧪 Testing

### Run Tests

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_nearby.py -v

# Run only unit tests
pytest tests/test_services.py -v
```

### Load Testing

```bash
# Start Locust web UI
locust -f locust/locustfile.py --host http://localhost:8000

# Open http://localhost:8089 and configure:
# - Number of users: 100
# - Spawn rate: 10/s
```

### Test Categories

| Test File | Coverage |
|-----------|----------|
| `test_health.py` | Health endpoints, security headers |
| `test_nearby.py` | Nearby search, validation, pagination |
| `test_bbox.py` | Bounding box search, edge cases |
| `test_pois.py` | CRUD operations, categories |
| `test_services.py` | Service layer unit tests |
| `test_websocket.py` | WebSocket connections, subscriptions |

---

## 📁 Project Structure

```
geosearch-api/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app, lifespan, exception handlers
│   ├── routes.py          # API endpoints
│   ├── services.py        # Business logic
│   ├── schemas.py         # Pydantic models
│   ├── db.py              # Database configuration
│   ├── cache.py           # Redis caching
│   ├── queries.py         # SQL queries
│   ├── settings.py        # Configuration
│   ├── middleware.py      # Custom middleware
│   ├── exceptions.py      # Custom exceptions
│   ├── health.py          # Health check endpoints
│   ├── websocket.py       # WebSocket support
│   └── logging_config.py  # Structured logging
├── tests/
│   ├── conftest.py        # Pytest fixtures
│   ├── test_health.py
│   ├── test_nearby.py
│   ├── test_bbox.py
│   ├── test_pois.py
│   ├── test_services.py
│   └── test_websocket.py
├── scripts/
│   ├── seed_synthetic.py  # Generate test data
│   └── seed_from_csv.py   # Import from CSV
├── locust/
│   └── locustfile.py      # Load test scenarios
├── .github/
│   └── workflows/
│       ├── ci.yml         # CI pipeline
│       └── release.yml    # Release automation
├── docker-compose.yml     # Development environment
├── docker-compose.prod.yml
├── Dockerfile             # Multi-stage production build
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── pyproject.toml         # Project configuration
└── README.md
```

---

## 🔒 Security

### Production Checklist

- [ ] Enable HTTPS (configure at load balancer)
- [ ] Set specific `CORS_ORIGINS` (not `*`)
- [ ] Enable `API_KEY_ENABLED` for authentication
- [ ] Use AWS Secrets Manager or Vault for secrets
- [ ] Configure rate limiting appropriately
- [ ] Enable structured JSON logging
- [ ] Set up monitoring and alerting
- [ ] Run as non-root user (done in Dockerfile)
- [ ] Regular dependency updates

### API Key Authentication

```bash
# Enable in environment
API_KEY_ENABLED=true
API_KEYS=key1,key2,key3

# Use in requests
curl -H "X-API-Key: key1" http://localhost:8000/v1/nearby?lat=29.76&lon=-95.36
```

---

## 📊 Monitoring

### Health Checks

```bash
# Basic health (for load balancers)
curl http://localhost:8000/health

# Detailed health with dependencies
curl http://localhost:8000/health/ready

# System statistics
curl http://localhost:8000/health/stats
```

### Structured Logs

```json
{
  "timestamp": "2026-01-12T10:30:00.000Z",
  "level": "INFO",
  "logger": "app.middleware",
  "message": "GET /v1/nearby - 200",
  "request_id": "abc-123",
  "method": "GET",
  "path": "/v1/nearby",
  "status_code": 200,
  "duration_ms": 12.5,
  "client_ip": "192.168.1.1"
}
```

### Response Headers

Every response includes:
- `X-Request-ID`: Unique request identifier
- `X-Response-Time`: Request duration
- `X-RateLimit-Limit`: Rate limit cap
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest`
5. Run linting: `ruff check app/`
6. Commit: `git commit -m 'Add amazing feature'`
7. Push: `git push origin feature/amazing-feature`
8. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ❤️ for the geospatial community
</p>
