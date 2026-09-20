import asyncio
import pytest
from api_aggregator.cache import AsyncCache


@pytest.mark.asyncio
async def test_cache_set_and_get():
    cache = AsyncCache()
    await cache.set("k1", "v1")
    val = await cache.get("k1")
    assert val == "v1"


@pytest.mark.asyncio
async def test_cache_miss():
    cache = AsyncCache()
    val = await cache.get("nonexistent")
    assert val is None
    assert cache.misses == 1


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    cache = AsyncCache(default_ttl=0.05)
    await cache.set("temp", "data")
    assert await cache.get("temp") == "data"

    await asyncio.sleep(0.06)
    assert await cache.get("temp") is None


@pytest.mark.asyncio
async def test_cache_lru_eviction():
    cache = AsyncCache(max_size=2)
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.set("c", 3)

    assert await cache.get("a") is None
    assert await cache.get("b") == 2
    assert await cache.get("c") == 3
    assert cache.evictions == 1


@pytest.mark.asyncio
async def test_cache_delete_and_clear():
    cache = AsyncCache()
    await cache.set("x", 10)
    assert await cache.delete("x") is True
    assert await cache.delete("x") is False

    await cache.set("y", 20)
    await cache.clear()
    assert await cache.get("y") is None


@pytest.mark.asyncio
async def test_cache_stats():
    cache = AsyncCache(max_size=10)
    await cache.set("m1", 100)
    await cache.get("m1")
    await cache.get("m2")

    stats = await cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_ratio"] == 0.5
    assert stats["size"] == 1
