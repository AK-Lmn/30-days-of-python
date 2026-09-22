import pytest


def test_audit_logs_lifecycle(client, sample_flag_data):
    client.post("/api/v1/flags", json=sample_flag_data)
    client.put(
        f"/api/v1/flags/{sample_flag_data['key']}",
        json={"description": "new description"},
    )
    client.patch(f"/api/v1/flags/{sample_flag_data['key']}/toggle")
    client.delete(f"/api/v1/flags/{sample_flag_data['key']}")

    logs_res = client.get("/api/v1/audit-logs")
    assert logs_res.status_code == 200
    data = logs_res.json()
    assert data["pagination"]["total"] == 4

    actions = [entry["action"] for entry in data["items"]]
    assert actions == ["DELETED", "TOGGLED", "UPDATED", "CREATED"]


def test_audit_logs_filtered_by_key(client, sample_flag_data):
    client.post("/api/v1/flags", json=sample_flag_data)
    client.post(
        "/api/v1/flags",
        json={
            "key": "another-flag",
            "name": "Another",
            "default_value": True,
        },
    )

    filtered_res = client.get(f"/api/v1/audit-logs?flag_key={sample_flag_data['key']}")
    assert filtered_res.status_code == 200
    data = filtered_res.json()
    assert data["pagination"]["total"] == 1
    assert data["items"][0]["flag_key"] == sample_flag_data["key"]
