"""
Tests for bounding box search endpoint.
"""
import pytest
from fastapi.testclient import TestClient


class TestBBoxSearch:
    """Test bounding box search endpoint."""
    
    def test_bbox_basic(self, client: TestClient, sample_pois, houston_bbox):
        """Test basic bounding box search."""
        response = client.get("/v1/bbox", params=houston_bbox)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "count" in data
        assert "bounds" in data
        assert data["bounds"]["min_lat"] == houston_bbox["min_lat"]
        assert data["bounds"]["max_lat"] == houston_bbox["max_lat"]
    
    def test_bbox_with_category(self, client: TestClient, sample_pois, houston_bbox):
        """Test bounding box search with category filter."""
        params = {**houston_bbox, "category": "restaurant"}
        
        response = client.get("/v1/bbox", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should be restaurants
        for item in data["items"]:
            assert item["category"] == "restaurant"
    
    def test_bbox_with_pagination(self, client: TestClient, sample_pois, houston_bbox):
        """Test bounding box search with pagination."""
        params = {**houston_bbox, "limit": 5, "offset": 0}
        
        response = client.get("/v1/bbox", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5
    
    def test_bbox_invalid_bounds(self, client: TestClient):
        """Test bounding box with invalid bounds (min > max)."""
        response = client.get(
            "/v1/bbox",
            params={
                "min_lat": 30,  # min > max
                "max_lat": 29,
                "min_lon": -95,
                "max_lon": -94,
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_bbox_invalid_lat_range(self, client: TestClient):
        """Test bounding box with latitude out of range."""
        response = client.get(
            "/v1/bbox",
            params={
                "min_lat": -100,  # Invalid
                "max_lat": 29,
                "min_lon": -95,
                "max_lon": -94,
            }
        )
        
        assert response.status_code == 422
    
    def test_bbox_missing_params(self, client: TestClient):
        """Test bounding box without required parameters."""
        response = client.get(
            "/v1/bbox",
            params={"min_lat": 29, "min_lon": -95}  # Missing max_lat, max_lon
        )
        
        assert response.status_code == 422
    
    def test_bbox_results_within_bounds(self, client: TestClient, sample_pois, houston_bbox):
        """Test all results are within the bounding box."""
        response = client.get("/v1/bbox", params=houston_bbox)
        
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            assert houston_bbox["min_lat"] <= item["lat"] <= houston_bbox["max_lat"]
            assert houston_bbox["min_lon"] <= item["lon"] <= houston_bbox["max_lon"]
    
    def test_bbox_cache_indicator(self, client: TestClient, houston_bbox):
        """Test cache indicator in response."""
        response = client.get("/v1/bbox", params=houston_bbox)
        
        assert response.status_code == 200
        data = response.json()
        assert "cached" in data
        assert isinstance(data["cached"], bool)


class TestBBoxEdgeCases:
    """Test edge cases for bounding box search."""
    
    def test_bbox_very_small_area(self, client: TestClient):
        """Test bounding box with very small area."""
        response = client.get(
            "/v1/bbox",
            params={
                "min_lat": 29.76040,
                "max_lat": 29.76041,
                "min_lon": -95.36980,
                "max_lon": -95.36979,
            }
        )
        
        assert response.status_code == 200
    
    def test_bbox_large_area(self, client: TestClient):
        """Test bounding box with large area."""
        response = client.get(
            "/v1/bbox",
            params={
                "min_lat": 29.0,
                "max_lat": 30.0,
                "min_lon": -96.0,
                "max_lon": -95.0,
            }
        )
        
        assert response.status_code == 200
    
    def test_bbox_at_boundaries(self, client: TestClient):
        """Test bounding box at coordinate boundaries."""
        response = client.get(
            "/v1/bbox",
            params={
                "min_lat": -90,
                "max_lat": 90,
                "min_lon": -180,
                "max_lon": 180,
            }
        )
        
        assert response.status_code == 200
