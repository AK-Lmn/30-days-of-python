import random
import time
from urllib.parse import urlparse


class RateLimiter:
    def __init__(self) -> None:
        self.last_request_times: dict[str, float] = {}

    def extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc.lower() or "default"

    def calculate_delay(self, base_delay: float, jitter: float) -> float:
        if jitter <= 0:
            return max(0.0, base_delay)
        jitter_offset = random.uniform(-jitter, jitter)
        return max(0.0, base_delay + jitter_offset)

    def wait(self, url: str, base_delay: float, jitter: float = 0.0) -> float:
        domain = self.extract_domain(url)
        now = time.monotonic()
        last_time = self.last_request_times.get(domain, 0.0)
        target_delay = self.calculate_delay(base_delay, jitter)

        elapsed = now - last_time
        sleep_duration = 0.0
        if elapsed < target_delay:
            sleep_duration = target_delay - elapsed
            time.sleep(sleep_duration)

        self.last_request_times[domain] = time.monotonic()
        return sleep_duration

    def reset(self) -> None:
        self.last_request_times.clear()
