import pytest


def test_evaluate_single_rule_match(client, sample_flag_data):
    client.post("/api/v1/flags", json=sample_flag_data)

    eval_req = {
        "flag_key": sample_flag_data["key"],
        "context": {
            "entity_id": "user-42",
            "attributes": {"is_beta": True},
        },
    }
    res = client.post("/api/v1/evaluate", json=eval_req)
    assert res.status_code == 200
    data = res.json()
    assert data["flag_key"] == sample_flag_data["key"]
    assert data["value"] is True
    assert data["enabled"] is True
    assert data["reason"] == "RULE_MATCH"
    assert data["rule_id"] == "rule-beta"


def test_evaluate_single_default_value(client, sample_flag_data):
    client.post("/api/v1/flags", json=sample_flag_data)

    eval_req = {
        "flag_key": sample_flag_data["key"],
        "context": {
            "entity_id": "user-99",
            "attributes": {"is_beta": False},
        },
    }
    res = client.post("/api/v1/evaluate", json=eval_req)
    assert res.status_code == 200
    data = res.json()
    assert data["value"] is False
    assert data["reason"] == "DEFAULT_VALUE"
    assert data["rule_id"] is None


def test_evaluate_single_fallback_on_missing(client):
    eval_req = {
        "flag_key": "non-existent-flag",
        "context": {"entity_id": "u-1"},
        "default_fallback": "safe_default_val",
    }
    res = client.post("/api/v1/evaluate", json=eval_req)
    assert res.status_code == 200
    data = res.json()
    assert data["value"] == "safe_default_val"
    assert data["reason"] == "FLAG_NOT_FOUND_FALLBACK"


def test_evaluate_single_missing_error(client):
    eval_req = {
        "flag_key": "non-existent-flag",
        "context": {"entity_id": "u-1"},
    }
    res = client.post("/api/v1/evaluate", json=eval_req)
    assert res.status_code == 404


def test_evaluate_bulk(client):
    client.post(
        "/api/v1/flags",
        json={
            "key": "f1",
            "name": "Flag 1",
            "default_value": "val1",
            "flag_type": "string",
        },
    )
    client.post(
        "/api/v1/flags",
        json={
            "key": "f2",
            "name": "Flag 2",
            "default_value": 100,
            "flag_type": "number",
        },
    )

    bulk_req = {
        "context": {"entity_id": "bulk-user-1"},
    }
    res = client.post("/api/v1/evaluate-all", json=bulk_req)
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 2
    assert data["evaluations"]["f1"]["value"] == "val1"
    assert data["evaluations"]["f2"]["value"] == 100
