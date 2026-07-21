"""Redis-based caching layer for AI responses and frequently accessed data."""

import hashlib
import json
import logging
from typing import Optional, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import redis; gracefully fall back if not available
try:
    import redis.asyncio as aioredis
    _redis_available = True
except ImportError:
    _redis_available = False
    logger.warning("redis not installed; caching is disabled.")


class RedisCache:
    """Async Redis cache with TTL support. Falls back to no-op if Redis is unavailable."""

    def __init__(
        self,
        url: str = "",
        default_ttl: int = 300,
        rag_ttl: int = 1800,
        stats_ttl: int = 300,
    ):
        self.default_ttl = default_ttl
        self.rag_ttl = rag_ttl
        self.stats_ttl = stats_ttl
        self._client: Any = None
        self._url = url or settings.REDIS_URL

    async def _ensure_client(self) -> bool:
        """Lazily create Redis connection. Returns True if connected."""
        if not _redis_available:
            return False
        if self._client is not None:
            return True
        try:
            self._client = aioredis.from_url(self._url, decode_responses=True, socket_connect_timeout=2)
            await self._client.ping()
            return True
        except Exception:
            logger.warning("Cannot connect to Redis at %s; caching disabled.", self._url)
            self._client = None
            return False

    # ── Key helpers ──────────────────────────────────────────────

    @staticmethod
    def _hash_key(prefix: str, *parts: str) -> str:
        """Produce a deterministic cache key: prefix:sha256_hex[:64]"""
        raw = "|".join(parts)
        digest = hashlib.sha256(raw.encode()).hexdigest()[:64]
        return f"{prefix}:{digest}"

    # ── Generic get / set ────────────────────────────────────────

    async def get(self, key: str) -> Optional[str]:
        if not await self._ensure_client():
            return None
        try:
            return await self._client.get(key)
        except Exception as exc:
            logger.debug("Redis GET error: %s", exc)
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        if not await self._ensure_client():
            return
        try:
            await self._client.setex(key, ttl or self.default_ttl, value)
        except Exception as exc:
            logger.debug("Redis SET error: %s", exc)

    async def delete(self, key: str) -> None:
        if not await self._ensure_client():
            return
        try:
            await self._client.delete(key)
        except Exception as exc:
            logger.debug("Redis DELETE error: %s", exc)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern."""
        if not await self._ensure_client():
            return
        try:
            cursor = 0
            while True:
                cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.debug("Redis DELETE_PATTERN error: %s", exc)

    # ── Domain helpers ───────────────────────────────────────────

    async def get_ai_response(self, messages: list, user_id: str = "", model: str = "") -> Optional[str]:
        """Look up a cached AI response by message hash + user for isolation."""
        msgs_json = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        key = self._hash_key("ai", msgs_json, user_id, model)
        return await self.get(key)

    async def set_ai_response(self, messages: list, response: str, user_id: str = "", model: str = "", ttl: Optional[int] = None) -> None:
        """Cache an AI response (scoped to user for data isolation)."""
        msgs_json = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        key = self._hash_key("ai", msgs_json, user_id, model)
        await self.set(key, response, ttl or self.default_ttl)

    async def get_rag_result(self, question: str) -> Optional[dict]:
        """Look up cached RAG query result."""
        key = self._hash_key("rag", question)
        raw = await self.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    async def set_rag_result(self, question: str, result: dict, ttl: Optional[int] = None) -> None:
        """Cache a RAG query result."""
        key = self._hash_key("rag", question)
        await self.set(key, json.dumps(result, ensure_ascii=False), ttl or self.rag_ttl)

    async def get_stats(self, cache_key: str) -> Optional[dict]:
        """Look up cached stats/dashboard data."""
        raw = await self.get(f"stats:{cache_key}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    async def set_stats(self, cache_key: str, data: dict, ttl: Optional[int] = None) -> None:
        """Cache stats/dashboard data."""
        await self.set(f"stats:{cache_key}", json.dumps(data, ensure_ascii=False), ttl or self.stats_ttl)

    async def invalidate_stats(self) -> None:
        """Invalidate all cached stats."""
        await self.delete_pattern("stats:*")


# Singleton
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache
