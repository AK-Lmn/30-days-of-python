import pytest
from api_cli.db import (
    add_history_entry,
    clear_history,
    delete_environment,
    delete_saved_request,
    get_active_environment,
    get_environment,
    get_history_entry,
    get_saved_request,
    list_environments,
    list_history,
    list_saved_requests,
    save_environment,
    save_request,
    set_active_environment,
)
from api_cli.models import Environment, HistoryEntry, SavedRequest


@pytest.fixture
def test_db(tmp_path):
    return tmp_path / "test_api_cli.db"


def test_environment_crud(test_db):
    env = Environment(
        name="staging",
        base_url="https://staging.api.com",
        headers={"Authorization": "Bearer 123"},
        variables={"port": "8080"},
        updated_at="2026-09-16T12:00:00Z",
    )
    save_environment(env, test_db)

    fetched = get_environment("staging", test_db)
    assert fetched is not None
    assert fetched.name == "staging"
    assert fetched.base_url == "https://staging.api.com"
    assert fetched.headers == {"Authorization": "Bearer 123"}
    assert fetched.variables == {"port": "8080"}

    envs = list_environments(test_db)
    assert len(envs) == 1
    assert envs[0].name == "staging"

    assert delete_environment("staging", test_db) is True
    assert get_environment("staging", test_db) is None
    assert delete_environment("staging", test_db) is False


def test_active_environment_setting(test_db):
    assert get_active_environment(test_db) is None
    set_active_environment("production", test_db)
    assert get_active_environment(test_db) == "production"
    set_active_environment(None, test_db)
    assert get_active_environment(test_db) is None


def test_saved_request_crud(test_db):
    req = SavedRequest(
        name="get_users",
        method="GET",
        url="https://api.example.com/users",
        headers={"Accept": "application/json"},
        query_params={"limit": "10"},
        body=None,
        env_name="prod",
        created_at="2026-09-16T12:00:00Z",
    )
    save_request(req, test_db)

    fetched = get_saved_request("get_users", test_db)
    assert fetched is not None
    assert fetched.name == "get_users"
    assert fetched.method == "GET"
    assert fetched.url == "https://api.example.com/users"
    assert fetched.query_params == {"limit": "10"}

    saved_list = list_saved_requests(test_db)
    assert len(saved_list) == 1
    assert saved_list[0].name == "get_users"

    assert delete_saved_request("get_users", test_db) is True
    assert get_saved_request("get_users", test_db) is None


def test_history_operations(test_db):
    entry = HistoryEntry(
        timestamp="2026-09-16T12:00:00Z",
        method="POST",
        url="https://api.example.com/login",
        status_code=200,
        latency_ms=45.2,
        request_headers={"Content-Type": "application/json"},
        request_body='{"user":"ck"}',
        response_headers={"content-type": "application/json"},
        response_body='{"token":"xyz"}',
        size_bytes=15,
    )
    entry_id = add_history_entry(entry, test_db)
    assert entry_id > 0

    fetched = get_history_entry(entry_id, test_db)
    assert fetched is not None
    assert fetched.method == "POST"
    assert fetched.status_code == 200
    assert fetched.latency_ms == 45.2
    assert fetched.request_body == '{"user":"ck"}'

    history_items = list_history(limit=10, db_path=test_db)
    assert len(history_items) == 1

    cleared = clear_history(test_db)
    assert cleared == 1
    assert len(list_history(limit=10, db_path=test_db)) == 0
