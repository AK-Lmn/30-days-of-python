import pytest


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "service" in data
    assert "version" in data
    assert "docs_url" in data
    assert res.headers.get("x-request-id") is not None
    assert res.headers.get("x-process-time-ms") is not None


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["uptime_seconds"] >= 0


def test_metrics_endpoint(client, sample_flag_data):
    client.post("/api/v1/flags", json=sample_flag_data)
    client.post(
        "/api/v1/evaluate",
        json={"flag_key": sample_flag_data["key"], "context": {"entity_id": "usr-1"}},
    )

    res = client.get("/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["total_flags"] == 1
    assert data["enabled_flags"] == 1
    assert data["total_evaluations"] == 1
    assert data["evaluations_by_flag"][sample_flag_data["key"]] == 1
