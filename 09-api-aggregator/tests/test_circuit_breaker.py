import time
from api_aggregator.circuit_breaker import CircuitBreaker
from api_aggregator.models import CircuitState


def test_circuit_breaker_initial_state():
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout_seconds=1.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True


def test_circuit_breaker_trips_to_open():
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_seconds=1.0)
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True

    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


def test_circuit_breaker_transitions_to_half_open():
    cb = CircuitBreaker(
        "test", failure_threshold=1, recovery_timeout_seconds=0.1
    )
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False

    time.sleep(0.15)
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN


def test_circuit_breaker_recovers_to_closed():
    cb = CircuitBreaker(
        "test",
        failure_threshold=1,
        recovery_timeout_seconds=0.05,
        half_open_success_threshold=2,
    )
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    time.sleep(0.06)
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN

    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True


def test_circuit_breaker_fails_in_half_open():
    cb = CircuitBreaker(
        "test",
        failure_threshold=1,
        recovery_timeout_seconds=0.05,
        half_open_success_threshold=2,
    )
    cb.record_failure()
    time.sleep(0.06)
    cb.allow_request()
    assert cb.state == CircuitState.HALF_OPEN

    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


def test_circuit_breaker_reset():
    cb = CircuitBreaker("test", failure_threshold=1)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0
    assert cb.allow_request() is True
