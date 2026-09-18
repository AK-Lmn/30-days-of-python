import time
from web_scraper.cache import ResponseCache
from web_scraper.models import PageResponse


def test_cache_set_and_get(tmp_path):
    cache = ResponseCache(cache_dir=tmp_path)
    page = PageResponse(
        url="https://example.com/test",
        status_code=200,
        html="<html><body><h1>Test</h1></body></html>",
        latency_ms=45.2,
    )

    cache.set(page.url, page)
    assert cache.count() == 1

    cached = cache.get(page.url)
    assert cached is not None
    assert cached.url == page.url
    assert cached.status_code == 200
    assert cached.html == page.html
    assert cached.from_cache is True
    assert cached.latency_ms == 45.2


def test_cache_miss(tmp_path):
    cache = ResponseCache(cache_dir=tmp_path)
    assert cache.get("https://notfound.com") is None


def test_cache_failed_response_not_cached(tmp_path):
    cache = ResponseCache(cache_dir=tmp_path)
    failed_page = PageResponse(
        url="https://example.com/error",
        status_code=500,
        html="Internal Server Error",
        error="Server error",
    )
    cache.set(failed_page.url, failed_page)
    assert cache.count() == 0
    assert cache.get(failed_page.url) is None


def test_cache_expired(tmp_path):
    cache = ResponseCache(cache_dir=tmp_path)
    page = PageResponse(
        url="https://example.com/expired",
        status_code=200,
        html="<div>old data</div>",
    )
    cache.set(page.url, page)

    cache_file = cache.get_cache_file_path(page.url)
    assert cache_file.exists()

    time.sleep(0.05)
    cached = cache.get(page.url, max_age_seconds=0.01)
    assert cached is None
    assert not cache_file.exists()


def test_cache_clear(tmp_path):
    cache = ResponseCache(cache_dir=tmp_path)
    for i in range(3):
        cache.set(f"https://example.com/{i}", PageResponse(url=f"https://example.com/{i}", status_code=200, html="content"))
    assert cache.count() == 3

    cleared = cache.clear()
    assert cleared == 3
    assert cache.count() == 0
