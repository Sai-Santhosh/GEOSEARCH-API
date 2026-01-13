"""
Unit tests for service layer.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services import POIService, get_neighbors_geohash
from app.schemas import POICreate, POIUpdate
from app.exceptions import POINotFoundError, ValidationError


class TestGeohashHelpers:
    """Test geohash helper functions."""
    
    def test_get_neighbors_geohash(self):
        """Test geohash neighbors calculation."""
        result = get_neighbors_geohash(29.7604, -95.3698, precision=5)
        
        assert isinstance(result, list)
        assert len(result) == 9  # center + 8 neighbors
        assert all(len(gh) == 5 for gh in result)
    
    def test_get_neighbors_different_precision(self):
        """Test geohash with different precisions."""
        result_4 = get_neighbors_geohash(29.7604, -95.3698, precision=4)
        result_6 = get_neighbors_geohash(29.7604, -95.3698, precision=6)
        
        assert all(len(gh) == 4 for gh in result_4)
        assert all(len(gh) == 6 for gh in result_6)
    
    def test_get_neighbors_edge_coordinates(self):
        """Test geohash at edge coordinates."""
        # Near poles
        result_north = get_neighbors_geohash(89.0, 0.0, precision=5)
        result_south = get_neighbors_geohash(-89.0, 0.0, precision=5)
        
        assert len(result_north) == 9
        assert len(result_south) == 9
        
        # Near date line
        result_east = get_neighbors_geohash(0.0, 179.0, precision=5)
        result_west = get_neighbors_geohash(0.0, -179.0, precision=5)
        
        assert len(result_east) == 9
        assert len(result_west) == 9


class TestPOIServiceNearby:
    """Test POI service nearby search."""
    
    def test_nearby_search_returns_dict(self, db_session, sample_pois):
        """Test nearby search returns expected structure."""
        service = POIService(db_session)
        
        result = service.nearby_search(
            lat=29.7604,
            lon=-95.3698,
            radius_m=5000,
        )
        
        assert isinstance(result, dict)
        assert "items" in result
        assert "count" in result
        assert "center" in result
        assert "radius_m" in result
        assert "cached" in result
    
    def test_nearby_search_with_category_filter(self, db_session, sample_pois):
        """Test nearby search filters by category."""
        service = POIService(db_session)
        
        result = service.nearby_search(
            lat=29.7604,
            lon=-95.3698,
            radius_m=5000,
            category="cafe",
        )
        
        for item in result["items"]:
            assert item.category == "cafe"


class TestPOIServiceBBox:
    """Test POI service bounding box search."""
    
    def test_bbox_search_returns_dict(self, db_session, sample_pois, houston_bbox):
        """Test bbox search returns expected structure."""
        service = POIService(db_session)
        
        result = service.bbox_search(**houston_bbox)
        
        assert isinstance(result, dict)
        assert "items" in result
        assert "count" in result
        assert "bounds" in result
        assert "cached" in result
    
    def test_bbox_search_invalid_bounds(self, db_session):
        """Test bbox search with invalid bounds raises error."""
        service = POIService(db_session)
        
        with pytest.raises(ValidationError):
            service.bbox_search(
                min_lat=30,  # min > max
                max_lat=29,
                min_lon=-95,
                max_lon=-94,
            )


class TestPOIServiceCRUD:
    """Test POI service CRUD operations."""
    
    def test_get_poi(self, db_session, sample_pois):
        """Test getting a POI by ID."""
        service = POIService(db_session)
        poi_id = sample_pois[0]["id"]
        
        result = service.get_poi(poi_id)
        
        assert result.id == poi_id
        assert result.name == sample_pois[0]["name"]
    
    def test_get_poi_not_found(self, db_session):
        """Test getting non-existent POI raises error."""
        service = POIService(db_session)
        
        with pytest.raises(POINotFoundError):
            service.get_poi(999999)
    
    def test_create_poi(self, db_session):
        """Test creating a POI."""
        service = POIService(db_session)
        data = POICreate(
            name="New POI",
            category="cafe",
            lat=29.76,
            lon=-95.36,
        )
        
        result = service.create_poi(data)
        
        assert result.id is not None
        assert result.name == "New POI"
        assert result.category == "cafe"
    
    def test_update_poi(self, db_session, sample_pois):
        """Test updating a POI."""
        service = POIService(db_session)
        poi_id = sample_pois[0]["id"]
        data = POIUpdate(name="Updated Name")
        
        result = service.update_poi(poi_id, data)
        
        assert result.id == poi_id
        assert result.name == "Updated Name"
    
    def test_update_poi_not_found(self, db_session):
        """Test updating non-existent POI raises error."""
        service = POIService(db_session)
        data = POIUpdate(name="Updated")
        
        with pytest.raises(POINotFoundError):
            service.update_poi(999999, data)
    
    def test_delete_poi(self, db_session, sample_pois):
        """Test deleting a POI."""
        service = POIService(db_session)
        poi_id = sample_pois[0]["id"]
        
        result = service.delete_poi(poi_id)
        
        assert result is True
        
        # Verify deleted
        with pytest.raises(POINotFoundError):
            service.get_poi(poi_id)
    
    def test_delete_poi_not_found(self, db_session):
        """Test deleting non-existent POI raises error."""
        service = POIService(db_session)
        
        with pytest.raises(POINotFoundError):
            service.delete_poi(999999)


class TestPOIServiceCategories:
    """Test POI service category operations."""
    
    def test_get_categories(self, db_session, sample_pois):
        """Test getting categories with counts."""
        service = POIService(db_session)
        
        result = service.get_categories()
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        for category in result:
            assert hasattr(category, "name")
            assert hasattr(category, "count")
            assert category.count > 0
    
    def test_get_stats(self, db_session, sample_pois):
        """Test getting POI statistics."""
        service = POIService(db_session)
        
        result = service.get_stats()
        
        assert "total_pois" in result
        assert "category_count" in result
        assert result["total_pois"] >= len(sample_pois)
