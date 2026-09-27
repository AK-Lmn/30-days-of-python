import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_key_management_and_auth(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "keyuser@example.com",
            "username": "keyuser",
            "password": "Password123!",
        },
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "keyuser", "password": "Password123!"},
    )
    token = login.json()["data"]["access_token"]

    create_key_res = await client.post(
        "/api/v1/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "CI/CD Pipeline Key", "scopes": ["profile:read"]},
    )
    assert create_key_res.status_code == 201
    key_data = create_key_res.json()["data"]
    raw_api_key = key_data["api_key"]
    key_id = key_data["id"]

    assert raw_api_key.startswith("wauth_live_")

    profile_via_api_key = await client.get(
        "/api/v1/users/me",
        headers={"X-API-Key": raw_api_key},
    )
    assert profile_via_api_key.status_code == 200
    assert profile_via_api_key.json()["data"]["username"] == "keyuser"

    keys_list_res = await client.get(
        "/api/v1/keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert keys_list_res.status_code == 200
    assert len(keys_list_res.json()["data"]) >= 1

    revoke_res = await client.delete(
        f"/api/v1/keys/{key_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoke_res.status_code == 200

    rejected_via_api_key = await client.get(
        "/api/v1/users/me",
        headers={"X-API-Key": raw_api_key},
    )
    assert rejected_via_api_key.status_code == 401
