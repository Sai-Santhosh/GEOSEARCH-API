"""
GeoSearch API Load Testing with Locust.

Run with:
    locust -f locust/locustfile.py --host http://localhost:8000

Or via Docker Compose:
    docker compose --profile testing up locust
"""
import random
import string
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# Test data
HOUSTON = (29.7604, -95.3698)
CATEGORIES = ["cafe", "restaurant", "gas", "grocery", "park", "pharmacy", "school"]


def random_coords(center: tuple, spread: float = 0.05) -> tuple:
    """Generate random coordinates near a center point."""
    lat = center[0] + random.uniform(-spread, spread)
    lon = center[1] + random.uniform(-spread, spread)
    return lat, lon


def random_name() -> str:
    """Generate a random POI name."""
    prefix = random.choice(["The", "Best", "New", "Old", "Great"])
    suffix = random.choice(["Place", "Spot", "Corner", "Hub", "Center"])
    return f"{prefix} {suffix} {''.join(random.choices(string.ascii_uppercase, k=3))}"


class GeoSearchUser(HttpUser):
    """Simulates a typical GeoSearch API user."""
    
    wait_time = between(0.5, 2.0)
    
    def on_start(self):
        """Called when a user starts."""
        # Verify API is healthy
        response = self.client.get("/health")
        if response.status_code != 200:
            raise Exception("API health check failed")
    
    @task(10)
    def nearby_search(self):
        """Most common operation: nearby search."""
        lat, lon = random_coords(HOUSTON)
        radius = random.choice([500, 1000, 2000, 3000, 5000])
        limit = random.choice([10, 25, 50])
        
        self.client.get(
            "/v1/nearby",
            params={
                "lat": f"{lat:.5f}",
                "lon": f"{lon:.5f}",
                "radius_m": radius,
                "limit": limit,
            },
            name="/v1/nearby"
        )
    
    @task(5)
    def nearby_with_category(self):
        """Nearby search with category filter."""
        lat, lon = random_coords(HOUSTON)
        category = random.choice(CATEGORIES)
        
        self.client.get(
            "/v1/nearby",
            params={
                "lat": f"{lat:.5f}",
                "lon": f"{lon:.5f}",
                "radius_m": 2000,
                "category": category,
                "limit": 25,
            },
            name="/v1/nearby?category"
        )
    
    @task(3)
    def bbox_search(self):
        """Bounding box search."""
        center_lat, center_lon = random_coords(HOUSTON, spread=0.02)
        spread = random.uniform(0.02, 0.05)
        
        self.client.get(
            "/v1/bbox",
            params={
                "min_lat": center_lat - spread,
                "min_lon": center_lon - spread,
                "max_lat": center_lat + spread,
                "max_lon": center_lon + spread,
                "limit": 100,
            },
            name="/v1/bbox"
        )
    
    @task(2)
    def bbox_with_category(self):
        """Bounding box search with category."""
        category = random.choice(CATEGORIES)
        
        self.client.get(
            "/v1/bbox",
            params={
                "min_lat": 29.73,
                "min_lon": -95.40,
                "max_lat": 29.79,
                "max_lon": -95.33,
                "category": category,
                "limit": 50,
            },
            name="/v1/bbox?category"
        )
    
    @task(1)
    def list_categories(self):
        """Get categories list."""
        self.client.get("/v1/categories", name="/v1/categories")
    
    @task(1)
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/health", name="/health")


class POIWriteUser(HttpUser):
    """Simulates users who create/update POIs (less common)."""
    
    wait_time = between(5.0, 15.0)
    weight = 1  # Much less common than read users
    
    created_poi_ids: list = []
    
    @task(3)
    def create_poi(self):
        """Create a new POI."""
        lat, lon = random_coords(HOUSTON)
        
        response = self.client.post(
            "/v1/pois",
            json={
                "name": random_name(),
                "category": random.choice(CATEGORIES),
                "lat": lat,
                "lon": lon,
                "metadata": {"source": "load_test"},
            },
            name="/v1/pois [POST]"
        )
        
        if response.status_code == 201:
            poi_id = response.json().get("id")
            if poi_id:
                self.created_poi_ids.append(poi_id)
    
    @task(1)
    def get_poi(self):
        """Get a specific POI."""
        if not self.created_poi_ids:
            return
        
        poi_id = random.choice(self.created_poi_ids)
        self.client.get(f"/v1/pois/{poi_id}", name="/v1/pois/{id} [GET]")
    
    @task(1)
    def update_poi(self):
        """Update a POI."""
        if not self.created_poi_ids:
            return
        
        poi_id = random.choice(self.created_poi_ids)
        self.client.patch(
            f"/v1/pois/{poi_id}",
            json={"name": random_name()},
            name="/v1/pois/{id} [PATCH]"
        )


class StressTestUser(HttpUser):
    """High-frequency user for stress testing."""
    
    wait_time = between(0.1, 0.3)
    weight = 0  # Disabled by default, enable for stress tests
    
    @task
    def rapid_nearby(self):
        """Rapid nearby searches."""
        lat, lon = random_coords(HOUSTON)
        self.client.get(
            "/v1/nearby",
            params={"lat": lat, "lon": lon, "radius_m": 1000, "limit": 10},
            name="/v1/nearby [stress]"
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when a load test starts."""
    if isinstance(environment.runner, MasterRunner):
        print("Load test starting on master node")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when a load test stops."""
    print("Load test finished")
    
    # Print summary
    stats = environment.stats
    print(f"\n{'='*60}")
    print("LOAD TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    
    if stats.total.num_requests > 0:
        print(f"P50: {stats.total.get_response_time_percentile(0.50):.0f}ms")
        print(f"P95: {stats.total.get_response_time_percentile(0.95):.0f}ms")
        print(f"P99: {stats.total.get_response_time_percentile(0.99):.0f}ms")
