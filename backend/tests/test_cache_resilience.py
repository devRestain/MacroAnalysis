from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core import cache


class BrokenRedisClient:
    async def get(self, key):
        raise RuntimeError("redis down")

    async def set(self, key, value, ex=None):
        raise RuntimeError("redis down")

    async def delete(self, key):
        raise RuntimeError("redis down")

    async def incr(self, key):
        raise RuntimeError("redis down")

    async def expire(self, key, ttl):
        raise RuntimeError("redis down")


class CacheResilienceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        cache.clear_local_fallback_state()

    def tearDown(self) -> None:
        cache.clear_local_fallback_state()

    async def test_cache_functions_fall_back_gracefully_when_redis_fails(self) -> None:
        with patch("app.core.cache.get_redis", return_value=BrokenRedisClient()):
            await cache.cache_set("summary:v1", {"value": 1}, ttl=60)
            value = await cache.cache_get("summary:v1")
            await cache.cache_delete("summary:v1")
            missing = await cache.cache_get("summary:v1")

        self.assertEqual(value, {"value": 1})
        self.assertIsNone(missing)

    async def test_rate_limit_uses_fallback_counter_when_redis_fails(self) -> None:
        with patch("app.core.cache.get_redis", return_value=BrokenRedisClient()):
            first_allowed, first_remaining = await cache.check_rate_limit("ai:test", limit=1, window_seconds=60)
            second_allowed, second_remaining = await cache.check_rate_limit("ai:test", limit=1, window_seconds=60)

        self.assertTrue(first_allowed)
        self.assertEqual(first_remaining, 0)
        self.assertFalse(second_allowed)
        self.assertEqual(second_remaining, 0)


if __name__ == "__main__":
    unittest.main()
