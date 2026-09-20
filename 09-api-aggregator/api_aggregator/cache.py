import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    created_at: float


class AsyncCache:
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._store:
                self.misses += 1
                return None
            entry = self._store[key]
            if time.time() > entry.expires_at:
                del self._store[key]
                self.misses += 1
                return None
            self._store.move_to_end(key)
            self.hits += 1
            return entry.value

    async def set(
        self, key: str, value: Any, ttl: Optional[float] = None
    ) -> None:
        async with self._lock:
            now = time.time()
            effective_ttl = ttl if ttl is not None else self.default_ttl
            expires_at = now + effective_ttl

            if key in self._store:
                self._store.move_to_end(key)
            elif len(self._store) >= self.max_size:
                self._store.popitem(last=False)
                self.evictions += 1

            self._store[key] = CacheEntry(
                value=value, expires_at=expires_at, created_at=now
            )

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def get_stats(self) -> dict[str, Any]:
        async with self._lock:
            now = time.time()
            expired_count = sum(
                1 for entry in self._store.values() if now > entry.expires_at
            )
            total_requests = self.hits + self.misses
            hit_ratio = (
                self.hits / total_requests if total_requests > 0 else 0.0
            )
            return {
                "size": len(self._store),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": round(hit_ratio, 4),
                "evictions": self.evictions,
                "expired_entries": expired_count,
            }
