import pytest


def test_list_flags_empty(client):
    response = client.get("/api/v1/flags")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["pagination"]["total"] == 0


def test_create_and_get_flag(client, sample_flag_data):
    create_res = client.post("/api/v1/flags", json=sample_flag_data)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["key"] == sample_flag_data["key"]
    assert created["enabled"] is True
    assert created["version"] == 1

    get_res = client.get(f"/api/v1/flags/{sample_flag_data['key']}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["key"] == sample_flag_data["key"]


def test_create_flag_duplicate_conflict(client, sample_flag_data):
    first_res = client.post("/api/v1/flags", json=sample_flag_data)
    assert first_res.status_code == 201

    second_res = client.post("/api/v1/flags", json=sample_flag_data)
    assert second_res.status_code == 409
    error_body = second_res.json()
    assert error_body["error"]["code"] in ("RESOURCE_CONFLICT", "FLAG_ALREADY_EXISTS")


def test_create_flag_invalid_key_validation(client):
    invalid_data = {
        "key": "INVALID KEY WITH SPACES",
        "name": "Invalid Flag",
        "default_value": False,
    }
    res = client.post("/api/v1/flags", json=invalid_data)
    assert res.status_code == 422
    error_body = res.json()
    assert error_body["error"]["code"] == "VALIDATION_ERROR"


def test_get_flag_not_found(client):
    res = client.get("/api/v1/flags/non-existent-key")
    assert res.status_code == 404
    error_body = res.json()
    assert error_body["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_update_flag(client, sample_flag_data):
    client.post("/api/v1/flags", json=sample_flag_data)
    update_payload = {
        "description": "Updated description here",
        "tags": ["checkout", "v2", "experimental"],
    }
    put_res = client.put(f"/api/v1/flags/{sample_flag_data['key']}", json=update_payload)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["description"] == "Updated description here"
    assert updated["version"] == 2
    assert "experimental" in updated["tags"]


def test_toggle_flag(client, sample_flag_data):
    client.post("/api/v1/flags", json=sample_flag_data)

    patch_res = client.patch(f"/api/v1/flags/{sample_flag_data['key']}/toggle")
    assert patch_res.status_code == 200
    assert patch_res.json()["enabled"] is False

    patch_res_2 = client.patch(f"/api/v1/flags/{sample_flag_data['key']}/toggle", json={"enabled": True})
    assert patch_res_2.status_code == 200
    assert patch_res_2.json()["enabled"] is True


def test_delete_flag(client, sample_flag_data):
    client.post("/api/v1/flags", json=sample_flag_data)

    del_res = client.delete(f"/api/v1/flags/{sample_flag_data['key']}")
    assert del_res.status_code == 204

    get_res = client.get(f"/api/v1/flags/{sample_flag_data['key']}")
    assert get_res.status_code == 404


def test_list_flags_filtering_and_pagination(client):
    for i in range(5):
        tag = "mobile" if i % 2 == 0 else "desktop"
        client.post(
            "/api/v1/flags",
            json={
                "key": f"flag-test-{i}",
                "name": f"Flag {i}",
                "default_value": i,
                "flag_type": "number",
                "tags": [tag],
                "enabled": i % 2 == 0,
            },
        )

    all_res = client.get("/api/v1/flags?limit=2&offset=0")
    assert all_res.status_code == 200
    assert len(all_res.json()["items"]) == 2
    assert all_res.json()["pagination"]["total"] == 5
    assert all_res.json()["pagination"]["has_more"] is True

    tag_res = client.get("/api/v1/flags?tag=mobile")
    assert tag_res.status_code == 200
    assert tag_res.json()["pagination"]["total"] == 3

    enabled_res = client.get("/api/v1/flags?enabled=true")
    assert enabled_res.status_code == 200
    assert enabled_res.json()["pagination"]["total"] == 3
