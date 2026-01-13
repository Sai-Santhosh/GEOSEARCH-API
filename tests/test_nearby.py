"""
Tests for nearby search endpoint.
"""
import pytest
from fastapi.testclient import TestClient


class TestNearbySearch:
    """Test nearby search endpoint."""
    
    def test_nearby_basic(self, client: TestClient, sample_pois, houston_center):
        """Test basic nearby search."""
        lat, lon = houston_center
        
        response = client.get(
            "/v1/nearby",
            params={"lat": lat, "lon": lon, "radius_m": 5000}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "count" in data
        assert "center" in data
        assert "radius_m" in data
        assert data["center"]["lat"] == lat
        assert data["center"]["lon"] == lon
        assert data["radius_m"] == 5000
    
    def test_nearby_with_category(self, client: TestClient, sample_pois, houston_center):
        """Test nearby search with category filter."""
        lat, lon = houston_center
        
        response = client.get(
            "/v1/nearby",
            params={
                "lat": lat,
                "lon": lon,
                "radius_m": 5000,
                "category": "cafe"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should be cafes
        for item in data["items"]:
            assert item["category"] == "cafe"
    
    def test_nearby_with_pagination(self, client: TestClient, sample_pois, houston_center):
        """Test nearby search with pagination."""
        lat, lon = houston_center
        
        # Get first page
        response1 = client.get(
            "/v1/nearby",
            params={
                "lat": lat,
                "lon": lon,
                "radius_m": 5000,
                "limit": 5,
                "offset": 0
            }
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["items"]) <= 5
        
        # Get second page
        response2 = client.get(
            "/v1/nearby",
            params={
                "lat": lat,
                "lon": lon,
                "radius_m": 5000,
                "limit": 5,
                "offset": 5
            }
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Pages should have different items (if enough data)
        if data1["items"] and data2["items"]:
            ids1 = {item["id"] for item in data1["items"]}
            ids2 = {item["id"] for item in data2["items"]}
            assert ids1.isdisjoint(ids2)
    
    def test_nearby_sorted_by_distance(self, client: TestClient, sample_pois, houston_center):
        """Test nearby results are sorted by distance."""
        lat, lon = houston_center
        
        response = client.get(
            "/v1/nearby",
            params={"lat": lat, "lon": lon, "radius_m": 5000}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check distances are in ascending order
        distances = [item.get("dist_m", 0) for item in data["items"] if item.get("dist_m") is not None]
        assert distances == sorted(distances)
    
    def test_nearby_invalid_lat(self, client: TestClient):
        """Test nearby with invalid latitude."""
        response = client.get(
            "/v1/nearby",
            params={"lat": 100, "lon": -95}  # lat > 90
        )
        
        assert response.status_code == 422
    
    def test_nearby_invalid_lon(self, client: TestClient):
        """Test nearby with invalid longitude."""
        response = client.get(
            "/v1/nearby",
            params={"lat": 29, "lon": -200}  # lon < -180
        )
        
        assert response.status_code == 422
    
    def test_nearby_radius_too_small(self, client: TestClient, houston_center):
        """Test nearby with radius below minimum."""
        lat, lon = houston_center
        
        response = client.get(
            "/v1/nearby",
            params={"lat": lat, "lon": lon, "radius_m": 10}  # min is 50
        )
        
        assert response.status_code == 422
    
    def test_nearby_radius_too_large(self, client: TestClient, houston_center):
        """Test nearby with radius above maximum."""
        lat, lon = houston_center
        
        response = client.get(
            "/v1/nearby",
            params={"lat": lat, "lon": lon, "radius_m": 100000}  # max is 50000
        )
        
        assert response.status_code == 422
    
    def test_nearby_missing_required_params(self, client: TestClient):
        """Test nearby without required parameters."""
        response = client.get("/v1/nearby")
        
        assert response.status_code == 422
    
    def test_nearby_cache_indicator(self, client: TestClient, houston_center):
        """Test cache indicator in response."""
        lat, lon = houston_center
        
        response = client.get(
            "/v1/nearby",
            params={"lat": lat, "lon": lon, "radius_m": 1000}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cached" in data
        assert isinstance(data["cached"], bool)
