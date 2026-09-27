import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_session_listing_and_revocation(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sessionuser@example.com",
            "username": "sessionuser",
            "password": "Password123!",
        },
    )

    login1 = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "sessionuser", "password": "Password123!"},
        headers={"User-Agent": "TestClient/1.0"},
    )
    token1 = login1.json()["data"]["access_token"]
    session1_id = login1.json()["data"]["session_id"]

    login2 = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "sessionuser", "password": "Password123!"},
        headers={"User-Agent": "TestClient/2.0"},
    )
    token2 = login2.json()["data"]["access_token"]
    session2_id = login2.json()["data"]["session_id"]

    assert session1_id != session2_id

    list_res = await client.get(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert list_res.status_code == 200
    sessions = list_res.json()["data"]
    assert len(sessions) >= 2

    revoke_res = await client.delete(
        f"/api/v1/sessions/{session2_id}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert revoke_res.status_code == 200

    check2 = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert check2.status_code == 401

    check1 = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert check1.status_code == 200
