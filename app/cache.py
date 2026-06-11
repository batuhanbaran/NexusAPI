import asyncio
import time
from typing import Any, Optional


class TTLCache:
    """Basit in-memory TTL cache — asyncio-safe, external dep yok."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._store[key] = (value, time.monotonic() + self._ttl)


mekan_cache: TTLCache = TTLCache(ttl_seconds=300)
