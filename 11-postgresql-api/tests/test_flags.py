import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_flag(client: AsyncClient):
    await client.post(
        "/api/v1/projects",
        json={"key": "flag-proj", "name": "Flag Project"},
    )

    create_flag_res = await client.post(
        "/api/v1/projects/flag-proj/flags",
        json={
            "key": "dark-theme",
            "name": "Dark Theme Mode",
            "description": "Enables sleek dark UI theme",
            "flag_type": "boolean",
            "default_value": False,
            "tags": ["frontend", "ui"],
        },
    )
    assert create_flag_res.status_code == 201
    flag_data = create_flag_res.json()
    assert flag_data["key"] == "dark-theme"
    assert len(flag_data["tags"]) == 2

    detail_res = await client.get("/api/v1/projects/flag-proj/flags/dark-theme")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["flag_states"]) == 3


@pytest.mark.asyncio
async def test_update_flag_environment_state_with_rules(client: AsyncClient):
    await client.post(
        "/api/v1/projects",
        json={"key": "rules-proj", "name": "Rules Project"},
    )
    await client.post(
        "/api/v1/projects/rules-proj/flags",
        json={
            "key": "checkout-banner",
            "name": "Checkout Promo Banner",
            "flag_type": "string",
            "default_value": "standard-banner",
            "tags": ["marketing"],
        },
    )

    update_res = await client.put(
        "/api/v1/projects/rules-proj/flags/checkout-banner/environments/production",
        json={
            "enabled": True,
            "percentage": 100,
            "variant_value": "black-friday-banner",
            "rules": [
                {
                    "priority": 0,
                    "name": "EU Region Offer",
                    "serve_value": "eu-special-banner",
                    "percentage": 100,
                    "conditions": [
                        {
                            "attribute": "country",
                            "operator": "in",
                            "values": ["DE", "FR", "NL"],
                        }
                    ],
                }
            ],
        },
    )
    assert update_res.status_code == 200
    state_data = update_res.json()
    assert state_data["enabled"] is True
    assert len(state_data["rules"]) == 1
    assert state_data["rules"][0]["name"] == "EU Region Offer"
    assert len(state_data["rules"][0]["conditions"]) == 1


@pytest.mark.asyncio
async def test_list_flags_filtering(client: AsyncClient):
    await client.post(
        "/api/v1/projects",
        json={"key": "filter-proj", "name": "Filter Project"},
    )
    await client.post(
        "/api/v1/projects/filter-proj/flags",
        json={
            "key": "flag-alpha",
            "name": "Alpha Feature",
            "tags": ["beta", "ai"],
        },
    )
    await client.post(
        "/api/v1/projects/filter-proj/flags",
        json={
            "key": "flag-beta",
            "name": "Beta Feature",
            "tags": ["stable"],
        },
    )

    tag_res = await client.get("/api/v1/projects/filter-proj/flags?tag=ai")
    assert tag_res.status_code == 200
    assert tag_res.json()["meta"]["total"] == 1
    assert tag_res.json()["items"][0]["key"] == "flag-alpha"

    search_res = await client.get("/api/v1/projects/filter-proj/flags?search=Beta")
    assert search_res.status_code == 200
    assert search_res.json()["meta"]["total"] == 1
    assert search_res.json()["items"][0]["key"] == "flag-beta"
