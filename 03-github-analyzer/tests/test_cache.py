import time
from pathlib import Path
from github_analyzer.cache import ResponseCache


def test_cache_set_and_get(tmp_path: Path):
    db_file = tmp_path / "test_cache.db"
    cache = ResponseCache(db_path=db_file)

    cache.set("user:octocat", {"name": "The Octocat", "followers": 100})
    result = cache.get("user:octocat")

    assert result is not None
    assert result["name"] == "The Octocat"
    assert result["followers"] == 100


def test_cache_miss(tmp_path: Path):
    db_file = tmp_path / "test_cache.db"
    cache = ResponseCache(db_path=db_file)

    assert cache.get("nonexistent_key") is None


def test_cache_ttl_expiration(tmp_path: Path):
    db_file = tmp_path / "test_cache.db"
    cache = ResponseCache(db_path=db_file)

    cache.set("expired_key", {"data": 123}, ttl_seconds=-1)
    result = cache.get("expired_key")
    assert result is None


def test_cache_delete(tmp_path: Path):
    db_file = tmp_path / "test_cache.db"
    cache = ResponseCache(db_path=db_file)

    cache.set("item_to_delete", "sample_val")
    deleted = cache.delete("item_to_delete")
    assert deleted is True
    assert cache.get("item_to_delete") is None


def test_cache_clear(tmp_path: Path):
    db_file = tmp_path / "test_cache.db"
    cache = ResponseCache(db_path=db_file)

    cache.set("key1", "val1")
    cache.set("key2", "val2")
    count = cache.clear()

    assert count == 2
    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_cache_prune_expired(tmp_path: Path):
    db_file = tmp_path / "test_cache.db"
    cache = ResponseCache(db_path=db_file)

    cache.set("valid", "val", ttl_seconds=3600)
    cache.set("expired1", "val", ttl_seconds=-10)
    cache.set("expired2", "val", ttl_seconds=-5)

    pruned = cache.prune_expired()
    assert pruned == 2
    assert cache.get("valid") == "val"
