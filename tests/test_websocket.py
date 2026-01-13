"""
Tests for WebSocket functionality.
"""
import pytest
from fastapi.testclient import TestClient


class TestWebSocket:
    """Test WebSocket endpoint."""
    
    def test_websocket_connect(self, client: TestClient):
        """Test WebSocket connection."""
        with client.websocket_connect("/ws") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "message" in data
    
    def test_websocket_ping_pong(self, client: TestClient):
        """Test WebSocket ping/pong."""
        with client.websocket_connect("/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send ping
            websocket.send_json({"type": "ping"})
            
            # Should receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"
    
    def test_websocket_subscribe(self, client: TestClient):
        """Test WebSocket channel subscription."""
        with client.websocket_connect("/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Subscribe to POI channel
            websocket.send_json({"type": "subscribe", "channel": "poi"})
            
            # Should receive subscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["channel"] == "poi"
    
    def test_websocket_unsubscribe(self, client: TestClient):
        """Test WebSocket channel unsubscription."""
        with client.websocket_connect("/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Subscribe first
            websocket.send_json({"type": "subscribe", "channel": "poi"})
            websocket.receive_json()
            
            # Unsubscribe
            websocket.send_json({"type": "unsubscribe", "channel": "poi"})
            
            # Should receive unsubscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "unsubscribed"
            assert data["channel"] == "poi"
    
    def test_websocket_unknown_message_type(self, client: TestClient):
        """Test WebSocket with unknown message type."""
        with client.websocket_connect("/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send unknown message type
            websocket.send_json({"type": "unknown_type"})
            
            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
    
    def test_websocket_stats_endpoint(self, client: TestClient):
        """Test WebSocket stats endpoint."""
        response = client.get("/ws/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_connections" in data
        assert "channels" in data


class TestWebSocketConnectionManager:
    """Test WebSocket connection manager."""
    
    def test_multiple_connections(self, client: TestClient):
        """Test multiple simultaneous connections."""
        with client.websocket_connect("/ws") as ws1:
            ws1.receive_json()  # Welcome
            
            with client.websocket_connect("/ws") as ws2:
                ws2.receive_json()  # Welcome
                
                # Both should be connected
                stats = client.get("/ws/stats").json()
                assert stats["total_connections"] >= 2
    
    def test_connection_cleanup(self, client: TestClient):
        """Test connections are cleaned up after disconnect."""
        initial_stats = client.get("/ws/stats").json()
        initial_count = initial_stats["total_connections"]
        
        # Create and close connection
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
        
        # Count should return to initial
        final_stats = client.get("/ws/stats").json()
        assert final_stats["total_connections"] == initial_count
