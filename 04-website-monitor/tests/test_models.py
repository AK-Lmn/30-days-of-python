import pytest
from website_monitor.models import (
    MonitorTarget,
    CheckResult,
    Incident,
    TargetStats,
)


def test_monitor_target_creation():
    target = MonitorTarget(
        url="https://example.com/api",
        name="Example API",
        method="post",
        expected_status=201,
        keyword="success",
        timeout_seconds=5.0,
        check_interval_seconds=30,
        headers={"Authorization": "Bearer token"},
        tags=["prod", "api"],
    )
    assert target.method == "POST"
    assert target.url == "https://example.com/api"
    assert target.name == "Example API"
    assert target.expected_status == 201
    assert target.keyword == "success"
    assert target.headers == {"Authorization": "Bearer token"}
    assert target.tags == ["prod", "api"]


def test_monitor_target_invalid_method():
    with pytest.raises(ValueError, match="Invalid HTTP method"):
        MonitorTarget(url="https://example.com", name="Test", method="INVALID")


def test_monitor_target_invalid_url():
    with pytest.raises(ValueError, match="URL must start with http"):
        MonitorTarget(url="ftp://example.com", name="Test")


def test_monitor_target_dict_roundtrip():
    target = MonitorTarget(
        id=42,
        url="https://example.com",
        name="Test",
        tags=["web"],
    )
    d = target.to_dict()
    assert d["id"] == 42
    assert d["url"] == "https://example.com"
    assert d["name"] == "Test"
    assert d["tags"] == ["web"]


def test_monitor_target_from_row():
    row = {
        "id": 1,
        "url": "https://service.org",
        "name": "Service",
        "method": "GET",
        "expected_status": 200,
        "keyword": None,
        "timeout_seconds": 10.0,
        "check_interval_seconds": 60,
        "headers": '{"X-Header": "Val"}',
        "request_body": None,
        "tags": '["api", "v1"]',
        "is_active": 1,
        "created_at": "2026-09-16T12:00:00Z",
    }
    t = MonitorTarget.from_row(row)
    assert t.id == 1
    assert t.headers == {"X-Header": "Val"}
    assert t.tags == ["api", "v1"]
    assert t.is_active is True


def test_check_result():
    cr = CheckResult(
        target_id=1,
        is_up=True,
        response_time_ms=123.456,
        status_code=200,
        ssl_days_left=90,
    )
    d = cr.to_dict()
    assert d["target_id"] == 1
    assert d["is_up"] is True
    assert d["response_time_ms"] == 123.46
    assert d["ssl_days_left"] == 90


def test_incident():
    inc = Incident(
        id=10,
        target_id=2,
        reason="HTTP 500",
        started_at="2026-09-16T10:00:00Z",
        ended_at="2026-09-16T10:05:00Z",
        duration_seconds=300.0,
        resolved=True,
    )
    d = inc.to_dict()
    assert d["id"] == 10
    assert d["resolved"] is True
    assert d["duration_seconds"] == 300.0


def test_target_stats():
    st = TargetStats(
        target_id=1,
        target_name="Core",
        target_url="https://core.io",
        total_checks=10,
        up_checks=9,
        down_checks=1,
        uptime_percentage=90.0,
        avg_latency_ms=50.2,
        min_latency_ms=20.0,
        p95_latency_ms=75.0,
        max_latency_ms=80.0,
        active_incident=False,
    )
    d = st.to_dict()
    assert d["uptime_percentage"] == 90.0
    assert d["total_checks"] == 10
