import time
from api_aggregator.models import CircuitState


class CircuitBreakerOpenException(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
        half_open_success_threshold: int = 2,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_success_threshold = half_open_success_threshold
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_state_change = time.time()

    def allow_request(self) -> bool:
        current_time = time.time()
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if current_time - self.last_state_change >= self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.consecutive_successes = 0
                self.last_state_change = current_time
                return True
            return False
        return True

    def record_success(self) -> None:
        self.consecutive_failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.half_open_success_threshold:
                self.state = CircuitState.CLOSED
                self.last_state_change = time.time()
                self.consecutive_successes = 0
        elif self.state == CircuitState.CLOSED:
            self.consecutive_successes += 1

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.state == CircuitState.CLOSED:
            if self.consecutive_failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_state_change = time.time()
