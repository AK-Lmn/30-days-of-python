from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from website_monitor.db import (
    init_db,
    add_target,
    get_target,
    get_target_by_url,
    list_targets,
    update_target,
    delete_target,
    record_check,
    get_recent_checks,
    open_incident,
    get_active_incident,
    resolve_incident,
    list_incidents,
    get_target_stats,
    get_all_target_stats,
    get_latency_history,
    prune_logs,
)
from website_monitor.models import MonitorTarget, CheckResult


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_monitor.db"
    init_db(db_file)
    return db_file


def test_target_crud(test_db: Path):
    target = MonitorTarget(
        url="https://api.test.org",
        name="Test API",
        tags=["staging", "v1"],
    )
    added = add_target(target, db_path=test_db)
    assert added.id is not None

    fetched = get_target(added.id, db_path=test_db)
    assert fetched is not None
    assert fetched.name == "Test API"
    assert fetched.tags == ["staging", "v1"]

    by_url = get_target_by_url("https://api.test.org", db_path=test_db)
    assert by_url is not None
    assert by_url.id == added.id

    fetched.name = "Updated API"
    fetched.expected_status = 204
    assert update_target(fetched, db_path=test_db) is True

    updated = get_target(added.id, db_path=test_db)
    assert updated is not None
    assert updated.name == "Updated API"
    assert updated.expected_status == 204

    by_tag = list_targets(tag="staging", db_path=test_db)
    assert len(by_tag) == 1

    by_other_tag = list_targets(tag="prod", db_path=test_db)
    assert len(by_other_tag) == 0

    assert delete_target(added.id, db_path=test_db) is True
    assert get_target(added.id, db_path=test_db) is None


def test_record_check_and_stats(test_db: Path):
    target = add_target(
        MonitorTarget(url="https://stats.test.org", name="Stats Target"),
        db_path=test_db,
    )
    assert target.id is not None

    record_check(
        CheckResult(target_id=target.id, is_up=True, response_time_ms=50.0, status_code=200),
        db_path=test_db,
    )
    record_check(
        CheckResult(target_id=target.id, is_up=True, response_time_ms=70.0, status_code=200),
        db_path=test_db,
    )
    record_check(
        CheckResult(target_id=target.id, is_up=False, response_time_ms=100.0, status_code=500),
        db_path=test_db,
    )

    recent = get_recent_checks(target_id=target.id, limit=10, db_path=test_db)
    assert len(recent) == 3

    stats = get_target_stats(target.id, db_path=test_db)
    assert stats is not None
    assert stats.total_checks == 3
    assert stats.up_checks == 2
    assert stats.down_checks == 1
    assert round(stats.uptime_percentage, 1) == 66.7
    assert stats.min_latency_ms == 50.0
    assert stats.max_latency_ms == 100.0

    history = get_latency_history(target.id, db_path=test_db)
    assert len(history) == 3

    all_stats = get_all_target_stats(db_path=test_db)
    assert len(all_stats) == 1


def test_incident_lifecycle(test_db: Path):
    target = add_target(
        MonitorTarget(url="https://outage.test.org", name="Outage Target"),
        db_path=test_db,
    )
    assert target.id is not None

    assert get_active_incident(target.id, db_path=test_db) is None

    inc = open_incident(target.id, reason="Gateway Timeout", db_path=test_db)
    assert inc.id is not None
    assert inc.resolved is False

    active = get_active_incident(target.id, db_path=test_db)
    assert active is not None
    assert active.id == inc.id

    dup_inc = open_incident(target.id, reason="Another error", db_path=test_db)
    assert dup_inc.id == inc.id

    resolved = resolve_incident(inc.id, db_path=test_db)
    assert resolved is not None
    assert resolved.resolved is True
    assert resolved.ended_at is not None

    assert get_active_incident(target.id, db_path=test_db) is None

    inc_list = list_incidents(target_id=target.id, db_path=test_db)
    assert len(inc_list) == 1


def test_prune_logs(test_db: Path):
    target = add_target(
        MonitorTarget(url="https://prune.test.org", name="Prune Target"),
        db_path=test_db,
    )
    assert target.id is not None

    old_date = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    old_res = CheckResult(
        target_id=target.id,
        is_up=True,
        response_time_ms=45.0,
        status_code=200,
        checked_at=old_date,
    )
    record_check(old_res, db_path=test_db)

    new_res = CheckResult(
        target_id=target.id,
        is_up=True,
        response_time_ms=45.0,
        status_code=200,
    )
    record_check(new_res, db_path=test_db)

    pruned = prune_logs(retention_days=30, db_path=test_db)
    assert pruned == 1
    assert len(get_recent_checks(target_id=target.id, db_path=test_db)) == 1
