"""
WebSocket support for real-time POI updates.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from .logging_config import get_logger
from .settings import settings

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.subscriptions: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from all subscriptions
        for channel, sockets in self.subscriptions.items():
            if websocket in sockets:
                sockets.remove(websocket)
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe a WebSocket to a channel."""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        
        if websocket not in self.subscriptions[channel]:
            self.subscriptions[channel].append(websocket)
            logger.debug(f"WebSocket subscribed to channel: {channel}")
    
    def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe a WebSocket from a channel."""
        if channel in self.subscriptions and websocket in self.subscriptions[channel]:
            self.subscriptions[channel].remove(websocket)
            logger.debug(f"WebSocket unsubscribed from channel: {channel}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send personal message: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected WebSockets."""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected sockets
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast a message to all subscribers of a channel."""
        if channel not in self.subscriptions:
            return
        
        disconnected = []
        
        for connection in self.subscriptions[channel]:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to channel {channel}: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected sockets
        for conn in disconnected:
            self.disconnect(conn)
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "channels": {
                channel: len(sockets)
                for channel, sockets in self.subscriptions.items()
            },
        }


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Supports the following message types:
    - subscribe: Subscribe to a channel (e.g., {"type": "subscribe", "channel": "poi"})
    - unsubscribe: Unsubscribe from a channel
    - ping: Heartbeat (responds with pong)
    
    Server sends:
    - poi_created: When a new POI is created
    - poi_updated: When a POI is updated
    - poi_deleted: When a POI is deleted
    - pong: Response to ping
    - error: Error message
    """
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "message": "Connected to GeoSearch WebSocket",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, websocket)
        
        while True:
            try:
                # Receive message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=60.0  # 60 second timeout
                )
                
                await handle_message(websocket, data)
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await manager.send_personal_message({
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def handle_message(websocket: WebSocket, data: dict):
    """Handle incoming WebSocket message."""
    msg_type = data.get("type")
    
    if msg_type == "subscribe":
        channel = data.get("channel", "poi")
        manager.subscribe(websocket, channel)
        await manager.send_personal_message({
            "type": "subscribed",
            "channel": channel,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, websocket)
    
    elif msg_type == "unsubscribe":
        channel = data.get("channel", "poi")
        manager.unsubscribe(websocket, channel)
        await manager.send_personal_message({
            "type": "unsubscribed",
            "channel": channel,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, websocket)
    
    elif msg_type == "ping":
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, websocket)
    
    else:
        await manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {msg_type}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, websocket)


async def broadcast_poi_event(event_type: str, poi_id: int, poi_data: dict | None = None):
    """Broadcast a POI event to all subscribers."""
    message = {
        "type": f"poi_{event_type}",
        "poi_id": poi_id,
        "data": poi_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    await manager.broadcast_to_channel("poi", message)
    logger.debug(f"Broadcasted POI event: {event_type} for POI {poi_id}")


@router.get(
    "/ws/stats",
    summary="WebSocket statistics",
    description="Get WebSocket connection statistics.",
    tags=["Monitoring"],
)
def websocket_stats():
    """Get WebSocket connection statistics."""
    return manager.get_stats()
