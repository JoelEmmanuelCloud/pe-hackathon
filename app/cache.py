import logging
import os
import time

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

logger = logging.getLogger(__name__)

_client = None
_down_until = 0.0

REDIRECT_TTL = int(os.getenv("CACHE_TTL", "300"))
RETRY_AFTER = int(os.getenv("CACHE_RETRY_AFTER", "30"))


def _mark_down(exc):
    global _client, _down_until
    _client = None
    _down_until = time.monotonic() + RETRY_AFTER
    logger.warning(
        "Redis unavailable, caching disabled",
        extra={"error": str(exc), "retry_after": RETRY_AFTER},
    )


def get_cache():
    global _client
    if _client is not None:
        return _client
    if time.monotonic() < _down_until:
        return None
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    try:
        client = redis.Redis(
            host=host,
            port=port,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            retry=Retry(NoBackoff(), 0),
        )
        client.ping()
        _client = client
        logger.info("Redis cache connected", extra={"host": host, "port": port})
    except Exception as exc:
        _mark_down(exc)
        return None
    return _client


def cache_ping() -> bool:
    cache = get_cache()
    if cache is None:
        return False
    try:
        return bool(cache.ping())
    except (redis.ConnectionError, redis.TimeoutError) as exc:
        _mark_down(exc)
        return False


def cache_get(key: str):
    cache = get_cache()
    if cache is None:
        return None
    try:
        return cache.get(key)
    except (redis.ConnectionError, redis.TimeoutError) as exc:
        _mark_down(exc)
        return None
    except Exception as exc:
        logger.warning("Cache GET failed", extra={"key": key, "error": str(exc)})
        return None


def cache_set(key: str, value: str, ttl: int = REDIRECT_TTL):
    cache = get_cache()
    if cache is None:
        return
    try:
        cache.setex(key, ttl, value)
    except (redis.ConnectionError, redis.TimeoutError) as exc:
        _mark_down(exc)
    except Exception as exc:
        logger.warning("Cache SET failed", extra={"key": key, "error": str(exc)})


def cache_delete(key: str):
    cache = get_cache()
    if cache is None:
        return
    try:
        cache.delete(key)
    except (redis.ConnectionError, redis.TimeoutError) as exc:
        _mark_down(exc)
    except Exception as exc:
        logger.warning("Cache DELETE failed", extra={"key": key, "error": str(exc)})


def redirect_cache_key(short_code: str) -> str:
    return f"url:redirect:v2:{short_code}"
