from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from .config import settings

try:
    import redis as redis_sync
except Exception:  # pragma: no cover - optional dependency in lightweight tests
    redis_sync = None

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover - optional dependency in lightweight tests
    aioredis = None

_redis: Any = None
_sync_redis: Any = None
_fallback_lock = threading.Lock()
_fallback_cache: dict[str, tuple[object, float | None]] = {}
_fallback_counters: dict[str, tuple[int, float]] = {}
_redis_warning_keys: set[str] = set()
logger = logging.getLogger(__name__)


def get_redis():
    global _redis
    if _redis is None:
        if aioredis is None:
            raise RuntimeError("redis asyncio client is not installed")
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def get_sync_redis():
    global _sync_redis
    if _sync_redis is None:
        if redis_sync is None:
            raise RuntimeError("redis client is not installed")
        _sync_redis = redis_sync.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _sync_redis


async def cache_get(key: str):
    try:
        r = get_redis()
        val = await r.get(key)
        if val:
            return json.loads(val)
        return None
    except Exception as exc:
        _warn_redis_failure("cache_get", exc)
        return _fallback_get(key)


async def cache_set(key: str, value, ttl: int = 3600):
    _fallback_set(key, value, ttl)
    try:
        r = get_redis()
        await r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as exc:
        _warn_redis_failure("cache_set", exc)


async def cache_delete(key: str):
    _fallback_delete(key)
    try:
        r = get_redis()
        await r.delete(key)
    except Exception as exc:
        _warn_redis_failure("cache_delete", exc)


async def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    try:
        r = get_redis()
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_seconds)
        remaining = max(limit - int(count), 0)
        return int(count) <= limit, remaining
    except Exception as exc:
        _warn_redis_failure("check_rate_limit", exc)
        count = _fallback_increment(key, window_seconds)
        remaining = max(limit - count, 0)
        return count <= limit, remaining


def cache_delete_sync(key: str) -> None:
    _fallback_delete(key)
    try:
        get_sync_redis().delete(key)
    except Exception as exc:
        _warn_redis_failure("cache_delete_sync", exc)


def cache_delete_pattern_sync(pattern: str) -> None:
    _fallback_delete_pattern(pattern)
    try:
        client = get_sync_redis()
        keys = list(client.scan_iter(match=pattern))
        if keys:
            client.delete(*keys)
    except Exception as exc:
        _warn_redis_failure("cache_delete_pattern_sync", exc)


def clear_local_fallback_state() -> None:
    with _fallback_lock:
        _fallback_cache.clear()
        _fallback_counters.clear()
        _redis_warning_keys.clear()


def _fallback_get(key: str):
    with _fallback_lock:
        entry = _fallback_cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and expires_at <= time.time():
            _fallback_cache.pop(key, None)
            return None
        return value


def _fallback_set(key: str, value, ttl: int) -> None:
    expires_at = time.time() + ttl if ttl else None
    with _fallback_lock:
        _fallback_cache[key] = (value, expires_at)


def _fallback_delete(key: str) -> None:
    with _fallback_lock:
        _fallback_cache.pop(key, None)
        _fallback_counters.pop(key, None)


def _fallback_delete_pattern(pattern: str) -> None:
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        with _fallback_lock:
            for key in list(_fallback_cache.keys()):
                if key.startswith(prefix):
                    _fallback_cache.pop(key, None)
            for key in list(_fallback_counters.keys()):
                if key.startswith(prefix):
                    _fallback_counters.pop(key, None)
        return
    _fallback_delete(pattern)


def _fallback_increment(key: str, window_seconds: int) -> int:
    now = time.time()
    with _fallback_lock:
        count, expires_at = _fallback_counters.get(key, (0, now + window_seconds))
        if expires_at <= now:
            count = 0
            expires_at = now + window_seconds
        count += 1
        _fallback_counters[key] = (count, expires_at)
        return count


def _warn_redis_failure(operation: str, exc: Exception) -> None:
    warning_key = f"{operation}:{type(exc).__name__}"
    if warning_key in _redis_warning_keys:
        return
    _redis_warning_keys.add(warning_key)
    logger.warning("Redis unavailable during %s; using graceful fallback: %s", operation, exc)
