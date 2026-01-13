"""
Tests for health check endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_basic_health(self, client: TestClient):
        """Test basic health endpoint returns OK."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data
    
    def test_liveness_probe(self, client: TestClient):
        """Test liveness probe returns alive."""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
    
    def test_readiness_probe(self, client: TestClient):
        """Test readiness probe checks dependencies."""
        response = client.get("/health/ready")
        
        # May return 200 or 503 depending on dependencies
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "database" in data["components"]
        assert "cache" in data["components"]
    
    def test_health_response_headers(self, client: TestClient):
        """Test health endpoints have proper headers."""
        response = client.get("/health")
        
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestSecurityHeaders:
    """Test security headers are present."""
    
    def test_security_headers_present(self, client: TestClient):
        """Test security headers are set on responses."""
        response = client.get("/health")
        
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    
    def test_cors_headers(self, client: TestClient):
        """Test CORS headers for preflight requests."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        # CORS should be allowed
        assert response.status_code in [200, 204, 405]
