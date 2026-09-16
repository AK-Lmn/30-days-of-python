from dataclasses import dataclass, field
import json
from typing import Any, Dict, Optional
from api_cli.config import DEFAULT_TIMEOUT_SECONDS


@dataclass
class RequestConfig:
    method: str = "GET"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    verify_ssl: bool = True
    follow_redirects: bool = True


@dataclass
class ResponseResult:
    status_code: int = 0
    reason_phrase: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    latency_ms: float = 0.0
    content_type: str = ""
    size_bytes: int = 0
    timestamp: str = ""

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400

    def parsed_json(self) -> Optional[Any]:
        if not self.body:
            return None
        try:
            return json.loads(self.body)
        except (ValueError, TypeError):
            return None


@dataclass
class Environment:
    name: str
    base_url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)
    updated_at: str = ""


@dataclass
class SavedRequest:
    name: str
    method: str = "GET"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    env_name: Optional[str] = None
    created_at: str = ""


@dataclass
class HistoryEntry:
    id: Optional[int] = None
    timestamp: str = ""
    method: str = "GET"
    url: str = ""
    status_code: int = 0
    latency_ms: float = 0.0
    request_headers: Dict[str, str] = field(default_factory=dict)
    request_body: Optional[str] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: str = ""
    size_bytes: int = 0


@dataclass
class BenchmarkStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time_seconds: float = 0.0
    requests_per_second: float = 0.0
    min_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    status_code_counts: Dict[int, int] = field(default_factory=dict)
