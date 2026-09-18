from web_scraper.rate_limiter import RateLimiter


def test_extract_domain():
    limiter = RateLimiter()
    assert limiter.extract_domain("https://example.com/path?arg=1") == "example.com"
    assert limiter.extract_domain("http://api.sub.domain.org:8080/test") == "api.sub.domain.org:8080"
    assert limiter.extract_domain("invalid-url") == "default"


def test_calculate_delay():
    limiter = RateLimiter()
    assert limiter.calculate_delay(1.5, 0.0) == 1.5
    with_jitter = limiter.calculate_delay(1.0, 0.2)
    assert 0.8 <= with_jitter <= 1.2
    assert limiter.calculate_delay(-1.0, 0.0) == 0.0


def test_rate_limiter_wait():
    limiter = RateLimiter()
    delay1 = limiter.wait("https://example.com/page1", base_delay=0.05, jitter=0.0)
    assert delay1 == 0.0

    delay2 = limiter.wait("https://example.com/page2", base_delay=0.05, jitter=0.0)
    assert delay2 >= 0.0

    other_domain_delay = limiter.wait("https://other.org/page1", base_delay=0.05, jitter=0.0)
    assert other_domain_delay == 0.0


def test_rate_limiter_reset():
    limiter = RateLimiter()
    limiter.wait("https://example.com/page1", base_delay=1.0)
    assert "example.com" in limiter.last_request_times
    limiter.reset()
    assert len(limiter.last_request_times) == 0
