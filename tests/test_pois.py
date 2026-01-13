"""
Tests for POI CRUD endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestPOICreate:
    """Test POI creation endpoint."""
    
    def test_create_poi(self, client: TestClient, sample_poi_data):
        """Test creating a new POI."""
        response = client.post("/v1/pois", json=sample_poi_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_poi_data["name"]
        assert data["category"] == sample_poi_data["category"]
        assert data["lat"] == sample_poi_data["lat"]
        assert data["lon"] == sample_poi_data["lon"]
    
    def test_create_poi_minimal(self, client: TestClient):
        """Test creating POI with minimal required fields."""
        minimal_data = {
            "name": "Minimal POI",
            "lat": 29.76,
            "lon": -95.36,
        }
        
        response = client.post("/v1/pois", json=minimal_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == minimal_data["name"]
        assert data["category"] is None
    
    def test_create_poi_with_metadata(self, client: TestClient):
        """Test creating POI with metadata."""
        poi_data = {
            "name": "POI with Metadata",
            "lat": 29.76,
            "lon": -95.36,
            "metadata": {
                "phone": "+1-555-1234",
                "website": "https://example.com",
                "hours": {"mon": "9-5", "tue": "9-5"},
            },
        }
        
        response = client.post("/v1/pois", json=poi_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["phone"] == "+1-555-1234"
    
    def test_create_poi_invalid_lat(self, client: TestClient):
        """Test creating POI with invalid latitude."""
        invalid_data = {
            "name": "Invalid POI",
            "lat": 100,  # Invalid
            "lon": -95,
        }
        
        response = client.post("/v1/pois", json=invalid_data)
        
        assert response.status_code == 422
    
    def test_create_poi_missing_name(self, client: TestClient):
        """Test creating POI without name."""
        invalid_data = {
            "lat": 29.76,
            "lon": -95.36,
        }
        
        response = client.post("/v1/pois", json=invalid_data)
        
        assert response.status_code == 422


class TestPOIRead:
    """Test POI read endpoint."""
    
    def test_get_poi(self, client: TestClient, sample_pois):
        """Test getting a POI by ID."""
        poi_id = sample_pois[0]["id"]
        
        response = client.get(f"/v1/pois/{poi_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == poi_id
        assert data["name"] == sample_pois[0]["name"]
    
    def test_get_poi_not_found(self, client: TestClient):
        """Test getting non-existent POI."""
        response = client.get("/v1/pois/999999")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NOT_FOUND"
    
    def test_get_poi_invalid_id(self, client: TestClient):
        """Test getting POI with invalid ID."""
        response = client.get("/v1/pois/invalid")
        
        assert response.status_code == 422


class TestPOIUpdate:
    """Test POI update endpoint."""
    
    def test_update_poi_name(self, client: TestClient, sample_pois):
        """Test updating POI name."""
        poi_id = sample_pois[0]["id"]
        
        response = client.patch(
            f"/v1/pois/{poi_id}",
            json={"name": "Updated Name"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
    
    def test_update_poi_category(self, client: TestClient, sample_pois):
        """Test updating POI category."""
        poi_id = sample_pois[0]["id"]
        
        response = client.patch(
            f"/v1/pois/{poi_id}",
            json={"category": "restaurant"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "restaurant"
    
    def test_update_poi_location(self, client: TestClient, sample_pois):
        """Test updating POI location."""
        poi_id = sample_pois[0]["id"]
        new_lat = 30.0
        new_lon = -96.0
        
        response = client.patch(
            f"/v1/pois/{poi_id}",
            json={"lat": new_lat, "lon": new_lon}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["lat"] == new_lat
        assert data["lon"] == new_lon
    
    def test_update_poi_not_found(self, client: TestClient):
        """Test updating non-existent POI."""
        response = client.patch(
            "/v1/pois/999999",
            json={"name": "Updated"}
        )
        
        assert response.status_code == 404


class TestPOIDelete:
    """Test POI delete endpoint."""
    
    def test_delete_poi(self, client: TestClient, sample_poi_data):
        """Test deleting a POI."""
        # First create a POI
        create_response = client.post("/v1/pois", json=sample_poi_data)
        poi_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/v1/pois/{poi_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify it's deleted
        get_response = client.get(f"/v1/pois/{poi_id}")
        assert get_response.status_code == 404
    
    def test_delete_poi_not_found(self, client: TestClient):
        """Test deleting non-existent POI."""
        response = client.delete("/v1/pois/999999")
        
        assert response.status_code == 404


class TestCategories:
    """Test categories endpoint."""
    
    def test_list_categories(self, client: TestClient, sample_pois):
        """Test listing all categories."""
        response = client.get("/v1/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "total" in data
        assert isinstance(data["categories"], list)
    
    def test_categories_have_counts(self, client: TestClient, sample_pois):
        """Test categories include counts."""
        response = client.get("/v1/categories")
        
        assert response.status_code == 200
        data = response.json()
        
        for category in data["categories"]:
            assert "name" in category
            assert "count" in category
            assert category["count"] > 0
