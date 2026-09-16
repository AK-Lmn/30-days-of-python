from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

VALID_HTTP_METHODS = {'GET', 'POST', 'HEAD', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'}


@dataclass
class MonitorTarget:
    url: str
    name: str
    id: Optional[int] = None
    method: str = 'GET'
    expected_status: int = 200
    keyword: Optional[str] = None
    timeout_seconds: float = 10.0
    check_interval_seconds: int = 60
    headers: Dict[str, str] = field(default_factory=dict)
    request_body: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        self.method = self.method.strip().upper()
        if self.method not in VALID_HTTP_METHODS:
            raise ValueError(f'Invalid HTTP method: {self.method}')
        self.url = self.url.strip()
        if not (self.url.startswith('http://') or self.url.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        self.name = self.name.strip()
        if not self.name:
            self.name = self.url
        if self.keyword:
            self.keyword = self.keyword.strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'url': self.url,
            'name': self.name,
            'method': self.method,
            'expected_status': self.expected_status,
            'keyword': self.keyword,
            'timeout_seconds': self.timeout_seconds,
            'check_interval_seconds': self.check_interval_seconds,
            'headers': self.headers,
            'request_body': self.request_body,
            'tags': self.tags,
            'is_active': self.is_active,
            'created_at': self.created_at,
        }

    @classmethod
    def from_row(cls, row: Any) -> 'MonitorTarget':
        headers_val = row['headers'] if hasattr(row, 'keys') else row[8]
        if isinstance(headers_val, str):
            try:
                headers = json.loads(headers_val)
            except Exception:
                headers = {}
        elif isinstance(headers_val, dict):
            headers = headers_val
        else:
            headers = {}

        tags_val = row['tags'] if hasattr(row, 'keys') else row[10]
        if isinstance(tags_val, str):
            try:
                tags = json.loads(tags_val)
            except Exception:
                tags = [t.strip() for t in tags_val.split(',') if t.strip()]
        elif isinstance(tags_val, list):
            tags = tags_val
        else:
            tags = []

        return cls(
            id=row['id'] if hasattr(row, 'keys') else row[0],
            url=row['url'] if hasattr(row, 'keys') else row[1],
            name=row['name'] if hasattr(row, 'keys') else row[2],
            method=row['method'] if hasattr(row, 'keys') else row[3],
            expected_status=row['expected_status'] if hasattr(row, 'keys') else row[4],
            keyword=row['keyword'] if hasattr(row, 'keys') else row[5],
            timeout_seconds=float(row['timeout_seconds'] if hasattr(row, 'keys') else row[6]),
            check_interval_seconds=int(row['check_interval_seconds'] if hasattr(row, 'keys') else row[7]),
            headers=headers,
            request_body=row['request_body'] if hasattr(row, 'keys') else row[9],
            tags=tags,
            is_active=bool(row['is_active'] if hasattr(row, 'keys') else row[11]),
            created_at=row['created_at'] if hasattr(row, 'keys') else row[12],
        )


@dataclass
class CheckResult:
    target_id: int
    is_up: bool
    response_time_ms: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    ssl_days_left: Optional[int] = None
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    target_name: Optional[str] = None
    target_url: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'target_id': self.target_id,
            'target_name': self.target_name,
            'target_url': self.target_url,
            'is_up': self.is_up,
            'status_code': self.status_code,
            'response_time_ms': round(self.response_time_ms, 2),
            'error_message': self.error_message,
            'ssl_days_left': self.ssl_days_left,
            'checked_at': self.checked_at,
        }

    @classmethod
    def from_row(cls, row: Any) -> 'CheckResult':
        return cls(
            id=row['id'] if hasattr(row, 'keys') else row[0],
            target_id=row['target_id'] if hasattr(row, 'keys') else row[1],
            is_up=bool(row['is_up'] if hasattr(row, 'keys') else row[2]),
            status_code=row['status_code'] if hasattr(row, 'keys') else row[3],
            response_time_ms=float(row['response_time_ms'] if hasattr(row, 'keys') else row[4]),
            error_message=row['error_message'] if hasattr(row, 'keys') else row[5],
            ssl_days_left=row['ssl_days_left'] if hasattr(row, 'keys') else row[6],
            checked_at=row['checked_at'] if hasattr(row, 'keys') else row[7],
            target_name=row['target_name'] if hasattr(row, 'keys') and 'target_name' in row.keys() else None,
            target_url=row['target_url'] if hasattr(row, 'keys') and 'target_url' in row.keys() else None,
        )


@dataclass
class Incident:
    target_id: int
    reason: str
    id: Optional[int] = None
    target_name: Optional[str] = None
    target_url: Optional[str] = None
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ended_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'target_id': self.target_id,
            'target_name': self.target_name,
            'target_url': self.target_url,
            'reason': self.reason,
            'started_at': self.started_at,
            'ended_at': self.ended_at,
            'duration_seconds': self.duration_seconds,
            'resolved': self.resolved,
        }

    @classmethod
    def from_row(cls, row: Any) -> 'Incident':
        return cls(
            id=row['id'] if hasattr(row, 'keys') else row[0],
            target_id=row['target_id'] if hasattr(row, 'keys') else row[1],
            reason=row['reason'] if hasattr(row, 'keys') else row[2],
            started_at=row['started_at'] if hasattr(row, 'keys') else row[3],
            ended_at=row['ended_at'] if hasattr(row, 'keys') else row[4],
            duration_seconds=float(row['duration_seconds']) if (hasattr(row, 'keys') and row['duration_seconds'] is not None) or (not hasattr(row, 'keys') and row[5] is not None) else None,
            resolved=bool(row['resolved'] if hasattr(row, 'keys') else row[6]),
            target_name=row['target_name'] if hasattr(row, 'keys') and 'target_name' in row.keys() else None,
            target_url=row['target_url'] if hasattr(row, 'keys') and 'target_url' in row.keys() else None,
        )


@dataclass
class TargetStats:
    target_id: int
    target_name: str
    target_url: str
    total_checks: int
    up_checks: int
    down_checks: int
    uptime_percentage: float
    avg_latency_ms: float
    min_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float
    active_incident: bool
    last_status_code: Optional[int] = None
    last_latency_ms: Optional[float] = None
    last_checked_at: Optional[str] = None
    last_is_up: Optional[bool] = None
    ssl_days_left: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'target_id': self.target_id,
            'target_name': self.target_name,
            'target_url': self.target_url,
            'total_checks': self.total_checks,
            'up_checks': self.up_checks,
            'down_checks': self.down_checks,
            'uptime_percentage': round(self.uptime_percentage, 2),
            'avg_latency_ms': round(self.avg_latency_ms, 2),
            'min_latency_ms': round(self.min_latency_ms, 2),
            'p95_latency_ms': round(self.p95_latency_ms, 2),
            'max_latency_ms': round(self.max_latency_ms, 2),
            'active_incident': self.active_incident,
            'last_status_code': self.last_status_code,
            'last_latency_ms': round(self.last_latency_ms, 2) if self.last_latency_ms is not None else None,
            'last_checked_at': self.last_checked_at,
            'last_is_up': self.last_is_up,
            'ssl_days_left': self.ssl_days_left,
        }
