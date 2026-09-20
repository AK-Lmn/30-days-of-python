import pytest
from api_aggregator.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_immediate_acquire():
    limiter = RateLimiter(rate=10.0, capacity=5.0)
    assert await limiter.acquire(1.0) is True
    assert await limiter.acquire(4.0) is True
    assert await limiter.acquire(1.0) is False


@pytest.mark.asyncio
async def test_rate_limiter_wait_and_acquire():
    limiter = RateLimiter(rate=50.0, capacity=2.0)
    assert await limiter.acquire(2.0) is True
    assert await limiter.acquire(1.0) is False

    success = await limiter.wait_and_acquire(tokens=1.0, timeout=0.2)
    assert success is True


@pytest.mark.asyncio
async def test_rate_limiter_timeout_exceeded():
    limiter = RateLimiter(rate=1.0, capacity=1.0)
    assert await limiter.acquire(1.0) is True
    success = await limiter.wait_and_acquire(tokens=5.0, timeout=0.05)
    assert success is False
