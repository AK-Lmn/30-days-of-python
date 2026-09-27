import time
from collections import defaultdict
from wardenauth.config import get_settings


class LoginRateLimiter:
    def __init__(self) -> None:
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._lockouts: dict[str, float] = {}

    def record_failure(self, identifier: str) -> tuple[int, bool]:
        settings = get_settings()
        now = time.time()
        window = settings.lockout_duration_minutes * 60
        self._failures[identifier] = [
            t for t in self._failures[identifier] if now - t < window
        ]
        self._failures[identifier].append(now)
        count = len(self._failures[identifier])
        if count >= settings.max_login_attempts:
            self._lockouts[identifier] = now + window
            return count, True
        return count, False

    def is_locked(self, identifier: str) -> tuple[bool, int]:
        now = time.time()
        lock_until = self._lockouts.get(identifier)
        if lock_until is not None:
            if now < lock_until:
                return True, int(lock_until - now)
            del self._lockouts[identifier]
            self._failures.pop(identifier, None)
        return False, 0

    def reset(self, identifier: str) -> None:
        self._failures.pop(identifier, None)
        self._lockouts.pop(identifier, None)

    def clear(self) -> None:
        self._failures.clear()
        self._lockouts.clear()


class RequestRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        window_start = now - window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        if len(self._requests[key]) >= max_requests:
            return False
        self._requests[key].append(now)
        return True

    def clear(self) -> None:
        self._requests.clear()


login_limiter = LoginRateLimiter()
request_limiter = RequestRateLimiter()
