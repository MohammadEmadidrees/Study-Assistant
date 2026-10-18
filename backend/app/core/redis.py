from typing import Optional, List
import json
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

class MemoryCacheFallback:
    """In-memory async fallback for development/testing when Redis is not running."""
    def __init__(self):
        self._cache: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> Optional[str]:
        return self._cache.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._cache[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._cache:
                del self._cache[k]
                count += 1
            if k in self._lists:
                del self._lists[k]
                count += 1
        return count

    async def rpush(self, key: str, *values: str) -> int:
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].extend(values)
        return len(self._lists[key])

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        items = self._lists.get(key, [])
        if end == -1:
            return items[start:]
        return items[start:end + 1]

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        if key in self._lists:
            if end == -1:
                self._lists[key] = self._lists[key][start:]
            else:
                self._lists[key] = self._lists[key][start:end + 1]
        return True

    async def close(self):
        pass


class RedisManager:
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
        self._fallback: Optional[MemoryCacheFallback] = None
        self.is_connected: bool = False

    async def connect(self):
        try:
            self.client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2.0
            )
            await self.client.ping()
            self.is_connected = True
            logger.info("Connected successfully to Redis server.")
        except Exception as e:
            logger.warning(f"Could not connect to Redis at {settings.REDIS_URL} ({e}). Using in-memory cache fallback.")
            self.client = None
            self._fallback = MemoryCacheFallback()
            self.is_connected = False

    async def close(self):
        if self.client:
            await self.client.aclose()
        if self._fallback:
            await self._fallback.close()

    def get_client(self):
        if self.is_connected and self.client:
            return self.client
        if not self._fallback:
            self._fallback = MemoryCacheFallback()
        return self._fallback


redis_manager = RedisManager()


async def get_redis():
    """Dependency for obtaining Redis client."""
    return redis_manager.get_client()
