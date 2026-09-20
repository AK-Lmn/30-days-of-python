import asyncio
import time


class RateLimiter:
    def __init__(self, rate: float = 10.0, capacity: float = 20.0) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill_timestamp = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill_timestamp
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill_timestamp = now

    async def acquire(self, tokens: float = 1.0) -> bool:
        async with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def wait_and_acquire(self, tokens: float = 1.0, timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            async with self._lock:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                needed = tokens - self.tokens
                sleep_duration = min(needed / self.rate, deadline - time.monotonic())
            if sleep_duration > 0:
                await asyncio.sleep(max(0.01, sleep_duration))
        return False
