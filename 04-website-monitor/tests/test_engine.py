from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import httpx
import pytest
from website_monitor.db import init_db, add_target, get_recent_checks, get_active_incident, list_incidents
from website_monitor.engine import MonitorEngine
from website_monitor.models import MonitorTarget


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_engine.db"
    init_db(db_file)
    return db_file


def test_engine_check_target_sync_records_to_db(test_db: Path):
    engine = MonitorEngine(db_path=test_db)
    target = add_target(MonitorTarget(url="https://api.test.org", name="Engine API"), db_path=test_db)

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = "All systems green"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = mock_resp

    with patch("website_monitor.checker.check_ssl_expiry", return_value=30):
        result = engine.check_target_sync(target, client=mock_client)

    assert result.is_up is True
    logs = get_recent_checks(target_id=target.id, db_path=test_db)
    assert len(logs) == 1
    assert logs[0].is_up is True


def test_engine_incident_lifecycle(test_db: Path):
    engine = MonitorEngine(db_path=test_db)
    target = add_target(MonitorTarget(url="https://flaky.test.org", name="Flaky API"), db_path=test_db)

    fail_resp = MagicMock(spec=httpx.Response)
    fail_resp.status_code = 500
    fail_resp.text = "Internal Server Error"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = fail_resp

    with patch("website_monitor.checker.check_ssl_expiry", return_value=None):
        engine.check_target_sync(target, client=mock_client)
        assert get_active_incident(target.id, db_path=test_db) is None

        engine.check_target_sync(target, client=mock_client)
        active_inc = get_active_incident(target.id, db_path=test_db)
        assert active_inc is not None
        assert active_inc.resolved is False

    ok_resp = MagicMock(spec=httpx.Response)
    ok_resp.status_code = 200
    ok_resp.text = "Recovered"
    mock_client.request.return_value = ok_resp

    with patch("website_monitor.checker.check_ssl_expiry", return_value=None):
        engine.check_target_sync(target, client=mock_client)
        assert get_active_incident(target.id, db_path=test_db) is None
        all_inc = list_incidents(target_id=target.id, db_path=test_db)
        assert len(all_inc) == 1
        assert all_inc[0].resolved is True


@pytest.mark.asyncio
async def test_engine_check_all_async(test_db: Path):
    engine = MonitorEngine(db_path=test_db)
    add_target(MonitorTarget(url="https://site1.org", name="Site 1"), db_path=test_db)
    add_target(MonitorTarget(url="https://site2.org", name="Site 2"), db_path=test_db)

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = "OK"

    with patch("website_monitor.checker.check_ssl_expiry", return_value=None):
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_resp
            results = await engine.check_all_async()

    assert len(results) == 2
    assert all(r.is_up for r in results)
