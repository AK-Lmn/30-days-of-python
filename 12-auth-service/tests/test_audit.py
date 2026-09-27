import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.core.hashing import hash_password
from wardenauth.models.entities import User


@pytest.mark.asyncio
async def test_audit_logs_and_system_stats(client: AsyncClient, test_session: AsyncSession):
    admin = User(
        email="auditadmin@example.com",
        username="auditadmin",
        password_hash=hash_password("AdminPassword123!"),
        role="admin",
        status="active",
    )
    test_session.add(admin)
    await test_session.commit()

    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "auditadmin", "password": "AdminPassword123!"},
    )
    admin_token = admin_login.json()["data"]["access_token"]

    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "audituser@example.com",
            "username": "audituser",
            "password": "Password123!",
        },
    )

    logs_res = await client.get(
        "/api/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert logs_res.status_code == 200
    logs_data = logs_res.json()
    assert logs_data["total"] >= 1
    event_types = [item["event_type"] for item in logs_data["items"]]
    assert "user.registered" in event_types or "auth.login.success" in event_types

    stats_res = await client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert stats_res.status_code == 200
    stats = stats_res.json()["data"]
    assert stats["total_users"] >= 2
    assert stats["active_users"] >= 2
    assert stats["active_sessions"] >= 1


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "wardenauth"
    assert "version" in data
