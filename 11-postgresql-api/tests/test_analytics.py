import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_project_analytics(client: AsyncClient):
    await client.post(
        "/api/v1/projects",
        json={"key": "analytics-proj", "name": "Analytics Proj"},
    )
    await client.post(
        "/api/v1/projects/analytics-proj/flags",
        json={
            "key": "bool-flag",
            "name": "Bool Flag",
            "flag_type": "boolean",
            "default_value": False,
            "tags": ["core", "infra"],
        },
    )
    await client.post(
        "/api/v1/projects/analytics-proj/flags",
        json={
            "key": "str-flag",
            "name": "Str Flag",
            "flag_type": "string",
            "default_value": "default",
            "tags": ["core"],
        },
    )

    await client.put(
        "/api/v1/projects/analytics-proj/flags/bool-flag/environments/production",
        json={
            "enabled": True,
            "rules": [
                {
                    "name": "Admin Rule",
                    "serve_value": True,
                    "conditions": [
                        {
                            "attribute": "role",
                            "operator": "equals",
                            "values": "admin",
                        }
                    ],
                }
            ],
        },
    )

    res = await client.get("/api/v1/projects/analytics-proj/analytics")
    assert res.status_code == 200
    data = res.json()
    assert data["total_flags"] == 2
    assert data["total_environments"] == 3
    assert data["flag_types"]["boolean"] == 1
    assert data["flag_types"]["string"] == 1

    tags_map = {item["tag_name"]: item["flag_count"] for item in data["tag_distribution"]}
    assert tags_map["core"] == 2
    assert tags_map["infra"] == 1

    prod_health = next(
        e for e in data["environments_health"] if e["environment_key"] == "production"
    )
    assert prod_health["total_flags"] == 2
    assert prod_health["enabled_flags"] == 1
    assert prod_health["disabled_flags"] == 1
    assert prod_health["rule_count"] == 1
