import logging
import os

import redis

logger = logging.getLogger(__name__)

_UNAVAILABLE = object()
_client = None

REDIRECT_TTL = int(os.getenv("CACHE_TTL", "300"))


def get_cache():
    global _client
    if _client is _UNAVAILABLE:
        return None
    if _client is None:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        try:
            client = redis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            client.ping()
            _client = client
            logger.info("Redis cache connected", extra={"host": host, "port": port})
        except Exception as exc:
            logger.warning(
                "Redis unavailable, caching disabled",
                extra={"error": str(exc)},
            )
            _client = _UNAVAILABLE
            return None
    return _client


def cache_get(key: str):
    cache = get_cache()
    if cache is None:
        return None
    try:
        return cache.get(key)
    except Exception as exc:
        logger.warning("Cache GET failed", extra={"key": key, "error": str(exc)})
        return None


def cache_set(key: str, value: str, ttl: int = REDIRECT_TTL):
    cache = get_cache()
    if cache is None:
        return
    try:
        cache.setex(key, ttl, value)
    except Exception as exc:
        logger.warning("Cache SET failed", extra={"key": key, "error": str(exc)})


def cache_delete(key: str):
    cache = get_cache()
    if cache is None:
        return
    try:
        cache.delete(key)
    except Exception as exc:
        logger.warning("Cache DELETE failed", extra={"key": key, "error": str(exc)})


def redirect_cache_key(short_code: str) -> str:
    return f"url:redirect:{short_code}"
