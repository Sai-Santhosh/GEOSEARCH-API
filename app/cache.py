"""
Production-grade Redis caching with connection pooling and health checks.
"""
import hashlib
from typing import Any

import orjson
import redis
from redis.exceptions import RedisError

from .logging_config import get_logger
from .settings import settings

logger = get_logger(__name__)


# Create connection pool
pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=settings.redis_max_connections,
    decode_responses=False,
)

# Redis client with connection pool
redis_client = redis.Redis(connection_pool=pool)


def _stable_key(prefix: str, payload: dict[str, Any]) -> str:
    """Generate a stable cache key from payload."""
    raw = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)
    digest = hashlib.sha256(raw).hexdigest()[:24]
    return f"geosearch:{prefix}:{digest}"


def cache_get(prefix: str, payload: dict[str, Any]) -> Any | None:
    """Get value from cache.
    
    Args:
        prefix: Cache key prefix
        payload: Cache key payload
        
    Returns:
        Cached value or None if not found/error
    """
    if not settings.cache_enabled:
        return None
    
    key = _stable_key(prefix, payload)
    try:
        blob = redis_client.get(key)
        if blob is None:
            logger.debug(f"Cache miss: {key}")
            return None
        
        logger.debug(f"Cache hit: {key}")
        return orjson.loads(blob)
    except RedisError as e:
        logger.warning(f"Cache get error: {e}")
        return None
    except orjson.JSONDecodeError as e:
        logger.warning(f"Cache decode error: {e}")
        return None


def cache_set(prefix: str, payload: dict[str, Any], value: Any, ttl: int | None = None) -> bool:
    """Set value in cache.
    
    Args:
        prefix: Cache key prefix
        payload: Cache key payload
        value: Value to cache
        ttl: Time to live in seconds (uses default if None)
        
    Returns:
        True if successful, False otherwise
    """
    if not settings.cache_enabled:
        return False
    
    key = _stable_key(prefix, payload)
    ttl = ttl if ttl is not None else settings.cache_ttl_seconds
    
    try:
        blob = orjson.dumps(value)
        redis_client.setex(key, ttl, blob)
        logger.debug(f"Cache set: {key} (ttl={ttl}s)")
        return True
    except RedisError as e:
        logger.warning(f"Cache set error: {e}")
        return False
    except (TypeError, orjson.JSONEncodeError) as e:
        logger.warning(f"Cache encode error: {e}")
        return False


def cache_delete(prefix: str, payload: dict[str, Any]) -> bool:
    """Delete value from cache.
    
    Args:
        prefix: Cache key prefix
        payload: Cache key payload
        
    Returns:
        True if deleted, False otherwise
    """
    key = _stable_key(prefix, payload)
    try:
        deleted = redis_client.delete(key)
        logger.debug(f"Cache delete: {key} (deleted={deleted})")
        return deleted > 0
    except RedisError as e:
        logger.warning(f"Cache delete error: {e}")
        return False


def cache_clear_prefix(prefix: str) -> int:
    """Clear all cached values with a given prefix.
    
    Args:
        prefix: Cache key prefix to clear
        
    Returns:
        Number of keys deleted
    """
    pattern = f"geosearch:{prefix}:*"
    try:
        keys = list(redis_client.scan_iter(match=pattern, count=1000))
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"Cache cleared: {prefix} ({deleted} keys)")
            return deleted
        return 0
    except RedisError as e:
        logger.warning(f"Cache clear error: {e}")
        return 0


def check_cache_health() -> dict:
    """Check Redis health and return status."""
    try:
        info = redis_client.info("server")
        memory = redis_client.info("memory")
        clients = redis_client.info("clients")
        
        return {
            "status": "healthy",
            "redis_version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "memory": {
                "used_memory_human": memory.get("used_memory_human", "unknown"),
                "used_memory_peak_human": memory.get("used_memory_peak_human", "unknown"),
                "maxmemory_human": memory.get("maxmemory_human", "unknown"),
            },
            "clients": {
                "connected": clients.get("connected_clients", 0),
                "blocked": clients.get("blocked_clients", 0),
            }
        }
    except RedisError as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def get_cache_stats() -> dict:
    """Get cache statistics."""
    try:
        info = redis_client.info("stats")
        keyspace = redis_client.info("keyspace")
        
        # Count GeoSearch keys
        geo_keys = len(list(redis_client.scan_iter(match="geosearch:*", count=1000)))
        
        return {
            "total_connections_received": info.get("total_connections_received", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0) / 
                max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            ),
            "geosearch_keys": geo_keys,
            "keyspace": keyspace,
        }
    except RedisError as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {"error": str(e)}


# Pub/Sub for real-time updates
class CachePubSub:
    """Redis Pub/Sub wrapper for real-time cache invalidation."""
    
    CHANNEL_PREFIX = "geosearch:events:"
    
    def __init__(self):
        self._pubsub = None
    
    def publish(self, channel: str, message: dict) -> int:
        """Publish a message to a channel."""
        full_channel = f"{self.CHANNEL_PREFIX}{channel}"
        try:
            data = orjson.dumps(message)
            return redis_client.publish(full_channel, data)
        except RedisError as e:
            logger.warning(f"Pub/Sub publish error: {e}")
            return 0
    
    def subscribe(self, channel: str):
        """Subscribe to a channel."""
        if self._pubsub is None:
            self._pubsub = redis_client.pubsub()
        
        full_channel = f"{self.CHANNEL_PREFIX}{channel}"
        self._pubsub.subscribe(full_channel)
        logger.info(f"Subscribed to channel: {full_channel}")
    
    def get_message(self, timeout: float = 1.0) -> dict | None:
        """Get next message from subscribed channels."""
        if self._pubsub is None:
            return None
        
        try:
            message = self._pubsub.get_message(timeout=timeout)
            if message and message["type"] == "message":
                return orjson.loads(message["data"])
            return None
        except (RedisError, orjson.JSONDecodeError) as e:
            logger.warning(f"Pub/Sub get_message error: {e}")
            return None
    
    def close(self):
        """Close the pub/sub connection."""
        if self._pubsub:
            self._pubsub.close()
            self._pubsub = None


pubsub = CachePubSub()
