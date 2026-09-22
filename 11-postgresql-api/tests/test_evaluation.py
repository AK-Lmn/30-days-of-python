import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_flag_evaluation_flow(client: AsyncClient):
    await client.post(
        "/api/v1/projects",
        json={"key": "eval-proj", "name": "Eval Project"},
    )
    await client.post(
        "/api/v1/projects/eval-proj/flags",
        json={
            "key": "dynamic-feature",
            "name": "Dynamic Feature",
            "flag_type": "string",
            "default_value": "standard-mode",
        },
    )

    disabled_eval = await client.post(
        "/api/v1/projects/eval-proj/environments/production/evaluate/dynamic-feature",
        json={"context": {"user_id": "usr-1"}},
    )
    assert disabled_eval.status_code == 200
    res = disabled_eval.json()
    assert res["enabled"] is False
    assert res["value"] == "standard-mode"
    assert res["reason"] == "FLAG_DISABLED"

    await client.put(
        "/api/v1/projects/eval-proj/flags/dynamic-feature/environments/production",
        json={
            "enabled": True,
            "percentage": 100,
            "variant_value": "fallback-active",
            "rules": [
                {
                    "priority": 0,
                    "name": "Beta Domain",
                    "serve_value": "beta-mode",
                    "percentage": 100,
                    "conditions": [
                        {
                            "attribute": "email",
                            "operator": "ends_with",
                            "values": "@beta.io",
                        }
                    ],
                },
                {
                    "priority": 1,
                    "name": "High Value Customers",
                    "serve_value": "vip-mode",
                    "percentage": 100,
                    "conditions": [
                        {
                            "attribute": "tier",
                            "operator": "equals",
                            "values": "platinum",
                        }
                    ],
                },
            ],
        },
    )

    match_rule_1 = await client.post(
        "/api/v1/projects/eval-proj/environments/production/evaluate/dynamic-feature",
        json={"context": {"user_id": "usr-2", "attributes": {"email": "alex@beta.io"}}},
    )
    assert match_rule_1.status_code == 200
    assert match_rule_1.json()["enabled"] is True
    assert match_rule_1.json()["value"] == "beta-mode"
    assert "Beta Domain" in match_rule_1.json()["reason"]

    match_rule_2 = await client.post(
        "/api/v1/projects/eval-proj/environments/production/evaluate/dynamic-feature",
        json={"context": {"user_id": "usr-3", "attributes": {"tier": "platinum"}}},
    )
    assert match_rule_2.status_code == 200
    assert match_rule_2.json()["value"] == "vip-mode"

    no_match_rule = await client.post(
        "/api/v1/projects/eval-proj/environments/production/evaluate/dynamic-feature",
        json={"context": {"user_id": "usr-4", "attributes": {"email": "alex@gmail.com"}}},
    )
    assert no_match_rule.status_code == 200
    assert no_match_rule.json()["value"] == "fallback-active"
    assert no_match_rule.json()["reason"] == "DEFAULT_TARGETING"


@pytest.mark.asyncio
async def test_bulk_evaluation(client: AsyncClient):
    await client.post(
        "/api/v1/projects",
        json={"key": "bulk-proj", "name": "Bulk Project"},
    )
    await client.post(
        "/api/v1/projects/bulk-proj/flags",
        json={"key": "flag-one", "name": "One", "flag_type": "boolean", "default_value": False},
    )
    await client.post(
        "/api/v1/projects/bulk-proj/flags",
        json={"key": "flag-two", "name": "Two", "flag_type": "string", "default_value": "off"},
    )

    bulk_res = await client.post(
        "/api/v1/projects/bulk-proj/environments/production/evaluate",
        json={"context": {"user_id": "usr-bulk"}},
    )
    assert bulk_res.status_code == 200
    results = bulk_res.json()["results"]
    assert "flag-one" in results
    assert "flag-two" in results
