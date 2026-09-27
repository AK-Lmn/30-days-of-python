import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.core.hashing import hash_password
from wardenauth.models.entities import User


@pytest.mark.asyncio
async def test_rbac_access_control(client: AsyncClient, test_session: AsyncSession):
    admin_user = User(
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("AdminPassword123!"),
        role="admin",
        status="active",
    )
    manager_user = User(
        email="manager@example.com",
        username="manager",
        password_hash=hash_password("ManagerPassword123!"),
        role="manager",
        status="active",
    )
    regular_user = User(
        email="regular@example.com",
        username="regular",
        password_hash=hash_password("UserPassword123!"),
        role="user",
        status="active",
    )
    test_session.add_all([admin_user, manager_user, regular_user])
    await test_session.commit()

    reg_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "regular", "password": "UserPassword123!"},
    )
    reg_token = reg_login.json()["data"]["access_token"]

    mgr_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "manager", "password": "ManagerPassword123!"},
    )
    mgr_token = mgr_login.json()["data"]["access_token"]

    adm_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin", "password": "AdminPassword123!"},
    )
    adm_token = adm_login.json()["data"]["access_token"]

    res_user_denied = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    assert res_user_denied.status_code == 403

    res_mgr_users = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert res_mgr_users.status_code == 200

    res_mgr_role_denied = await client.patch(
        f"/api/v1/admin/users/{regular_user.id}/role",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"role": "manager"},
    )
    assert res_mgr_role_denied.status_code == 403

    res_adm_role_update = await client.patch(
        f"/api/v1/admin/users/{regular_user.id}/role",
        headers={"Authorization": f"Bearer {adm_token}"},
        json={"role": "manager"},
    )
    assert res_adm_role_update.status_code == 200
    assert res_adm_role_update.json()["data"]["role"] == "manager"

    res_adm_suspend = await client.patch(
        f"/api/v1/admin/users/{regular_user.id}/status",
        headers={"Authorization": f"Bearer {adm_token}"},
        json={"status": "suspended"},
    )
    assert res_adm_suspend.status_code == 200

    suspended_try_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "regular", "password": "UserPassword123!"},
    )
    assert suspended_try_login.status_code == 403
