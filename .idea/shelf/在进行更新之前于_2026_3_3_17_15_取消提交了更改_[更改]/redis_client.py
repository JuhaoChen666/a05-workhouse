"""Redis client wrapper."""

from typing import Optional

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[redis.Redis] = None


async def init_redis() -> redis.Redis:
    """Initialize Redis connection."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning("Failed to connect to Redis", error=str(e))
            raise
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> Optional[redis.Redis]:
    """Get Redis client instance."""
    return _redis_client


class CacheManager:
    """Cache manager for common operations."""

    def __init__(self, redis_client: Optional[redis.Redis] = None) -> None:
        """Initialize cache manager."""
        self._redis = redis_client or _redis_client

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self._redis:
            return None
        return await self._redis.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache."""
        if not self._redis:
            return False
        ttl = ttl or settings.CACHE_TTL
        await self._redis.setex(key, ttl, value)
        return True

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self._redis:
            return False
        await self._redis.delete(key)
        return True

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._redis:
            return False
        return await self._redis.exists(key) > 0
