import random
from locust import HttpUser, task, between

HOUSTON = (29.7604, -95.3698)

class GeoUser(HttpUser):
    wait_time = between(0.2, 1.2)

    @task(4)
    def nearby(self):
        lat = HOUSTON[0] + random.uniform(-0.03, 0.03)
        lon = HOUSTON[1] + random.uniform(-0.03, 0.03)
        r = random.choice([500, 1000, 2000, 4000])
        self.client.get(f"/v1/nearby?lat={lat:.5f}&lon={lon:.5f}&radius_m={r}&limit=25")

    @task(1)
    def bbox(self):
        self.client.get("/v1/bbox?min_lat=29.73&min_lon=-95.40&max_lat=29.79&max_lon=-95.33&limit=200")
