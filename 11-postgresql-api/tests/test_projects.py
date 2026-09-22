import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    response = await client.post(
        "/api/v1/projects",
        json={
            "key": "alpha-platform",
            "name": "Alpha Platform",
            "description": "Primary trading platform",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "alpha-platform"
    assert data["name"] == "Alpha Platform"
    assert len(data["environments"]) == 3
    env_keys = {e["key"] for e in data["environments"]}
    assert env_keys == {"development", "staging", "production"}


@pytest.mark.asyncio
async def test_create_duplicate_project_fails(client: AsyncClient):
    payload = {
        "key": "duplicate-test",
        "name": "Original Project",
    }
    first_res = await client.post("/api/v1/projects", json=payload)
    assert first_res.status_code == 201

    second_res = await client.post("/api/v1/projects", json=payload)
    assert second_res.status_code == 409
    data = second_res.json()
    assert data["error"]["code"] == "PROJECT_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_list_and_get_projects(client: AsyncClient):
    await client.post("/api/v1/projects", json={"key": "project-one", "name": "One"})
    await client.post("/api/v1/projects", json={"key": "project-two", "name": "Two"})

    list_res = await client.get("/api/v1/projects")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["meta"]["total"] >= 2
    assert len(data["items"]) >= 2

    get_res = await client.get("/api/v1/projects/project-one")
    assert get_res.status_code == 200
    assert get_res.json()["key"] == "project-one"


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient):
    await client.post("/api/v1/projects", json={"key": "project-update", "name": "Before"})

    patch_res = await client.patch(
        "/api/v1/projects/project-update",
        json={"name": "After Update", "description": "Updated description"},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["name"] == "After Update"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_manage_environments(client: AsyncClient):
    await client.post("/api/v1/projects", json={"key": "env-test-project", "name": "Env Test"})

    add_env_res = await client.post(
        "/api/v1/projects/env-test-project/environments",
        json={"key": "qa", "name": "Quality Assurance"},
    )
    assert add_env_res.status_code == 201
    assert add_env_res.json()["key"] == "qa"

    dup_env_res = await client.post(
        "/api/v1/projects/env-test-project/environments",
        json={"key": "qa", "name": "Quality Assurance Duplicate"},
    )
    assert dup_env_res.status_code == 409

    del_env_res = await client.delete("/api/v1/projects/env-test-project/environments/qa")
    assert del_env_res.status_code == 204

    envs_res = await client.get("/api/v1/projects/env-test-project/environments")
    assert envs_res.status_code == 200
    env_keys = [e["key"] for e in envs_res.json()]
    assert "qa" not in env_keys
