import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_registration_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "username": "alice",
            "password": "Password123!",
            "full_name": "Alice Wonderland",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "alice@example.com"
    assert data["data"]["username"] == "alice"
    assert data["data"]["role"] == "user"
    assert data["data"]["status"] == "active"


@pytest.mark.asyncio
async def test_user_registration_duplicate_email(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "username": "user1",
        "password": "Password123!",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    payload["username"] = "user2"
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "USER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_user_registration_duplicate_username(client: AsyncClient):
    payload = {
        "email": "unique1@example.com",
        "username": "samename",
        "password": "Password123!",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    payload["email"] = "unique2@example.com"
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "USER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_user_registration_weak_passwords(client: AsyncClient):
    cases = [
        "short1!",
        "nouppercase123!",
        "NOLOWERCASE123!",
        "NoSpecialChar123",
        "NoDigitsHere!",
    ]
    for weak_pw in cases:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"weak_{len(weak_pw)}@example.com",
                "username": f"user_{len(weak_pw)}",
                "password": weak_pw,
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success_and_me_endpoint(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "username": "bobuser",
            "password": "Password123!",
        },
    )
    assert reg.status_code == 201

    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": "bobuser",
            "password": "Password123!",
        },
    )
    assert login_res.status_code == 200
    login_data = login_res.json()["data"]
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]
    assert access_token
    assert refresh_token

    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"]["username"] == "bobuser"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "charlie@example.com",
            "username": "charlie",
            "password": "Password123!",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": "charlie",
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_user_not_found(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": "nonexistent_user",
            "password": "Password123!",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_lifecycle_and_rotation(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "david@example.com",
            "username": "david",
            "password": "Password123!",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": "david",
            "password": "Password123!",
        },
    )
    original_refresh = login_res.json()["data"]["refresh_token"]

    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert refresh_res.status_code == 200
    refreshed_data = refresh_res.json()["data"]
    new_access = refreshed_data["access_token"]
    new_refresh = refreshed_data["refresh_token"]

    assert new_access
    assert new_refresh
    assert new_refresh != original_refresh

    reused_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert reused_res.status_code == 401


@pytest.mark.asyncio
async def test_logout_and_logout_all(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "elena@example.com",
            "username": "elena",
            "password": "Password123!",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": "elena",
            "password": "Password123!",
        },
    )
    token = login_res.json()["data"]["access_token"]

    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200

    after_logout_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after_logout_res.status_code == 401


@pytest.mark.asyncio
async def test_password_change_flow(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "frank@example.com",
            "username": "frank",
            "password": "OldPassword123!",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "frank", "password": "OldPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]

    change_res = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!",
        },
    )
    assert change_res.status_code == 200

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "frank", "password": "OldPassword123!"},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "frank", "password": "NewPassword123!"},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "grace@example.com",
            "username": "grace",
            "password": "InitialPassword123!",
        },
    )

    forgot_res = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "grace@example.com"},
    )
    assert forgot_res.status_code == 200
    reset_token = forgot_res.json()["data"]["reset_token"]
    assert reset_token

    confirm_res = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "ResetPassword123!",
        },
    )
    assert confirm_res.status_code == 200

    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": "grace",
            "password": "ResetPassword123!",
        },
    )
    assert login_res.status_code == 200
