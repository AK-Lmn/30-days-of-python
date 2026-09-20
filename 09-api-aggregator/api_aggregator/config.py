from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "API Aggregator"
    app_version: str = "0.1.0"
    default_host: str = "127.0.0.1"
    default_port: int = 8000
    default_timeout_seconds: float = 6.0
    default_cache_ttl_seconds: float = 300.0
    cache_max_size: int = 1000
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_recovery_timeout_seconds: float = 30.0
    circuit_breaker_half_open_success_threshold: int = 2
    rate_limiter_rate: float = 10.0
    rate_limiter_capacity: float = 20.0
    export_dir: Path = field(default_factory=lambda: Path("exports"))


CONFIG = AppConfig()
