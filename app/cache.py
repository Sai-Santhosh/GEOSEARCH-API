import hashlib
from typing import Any

import orjson
import redis

from .settings import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=False)

def _stable_key(prefix: str, payload: dict[str, Any]) -> str:
    raw = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)
    digest = hashlib.sha256(raw).hexdigest()[:24]
    return f"{prefix}:{digest}"

def cache_get(prefix: str, payload: dict[str, Any]) -> Any | None:
    key = _stable_key(prefix, payload)
    blob = redis_client.get(key)
    if blob is None:
        return None
    return orjson.loads(blob)

def cache_set(prefix: str, payload: dict[str, Any], value: Any, ttl: int) -> None:
    key = _stable_key(prefix, payload)
    redis_client.setex(key, ttl, orjson.dumps(value))
