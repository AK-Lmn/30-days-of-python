import pytest
from httpx import AsyncClient
from taskforge.core.enums import ScheduleType
from taskforge.repositories.job_repo import JobRepository


@pytest.mark.asyncio
async def test_api_queue_statistics(client: AsyncClient):
    await client.post("/api/v1/jobs", json={"task_name": "send_email", "queue": "q1"})
    await client.post("/api/v1/jobs", json={"task_name": "generate_report", "queue": "q2"})

    response = await client.get("/api/v1/queues")
    assert response.status_code == 200
    data = response.json()
    assert "queues" in data
    assert data["total_jobs"] >= 2
    queue_names = [q["queue"] for q in data["queues"]]
    assert "q1" in queue_names
    assert "q2" in queue_names


@pytest.mark.asyncio
async def test_api_worker_endpoints(client: AsyncClient, session_factory):
    async with session_factory() as session:
        repo = JobRepository(session)
        await repo.register_worker_heartbeat(
            worker_id="w-api-1",
            hostname="worker-node-1",
            pid=1234,
            queues=["default", "high"],
            concurrency=2,
            status="active",
        )

    response = await client.get("/api/v1/workers")
    assert response.status_code == 200
    workers = response.json()
    assert len(workers) == 1
    assert workers[0]["id"] == "w-api-1"
    assert workers[0]["queues"] == ["default", "high"]


@pytest.mark.asyncio
async def test_api_schedules_crud(client: AsyncClient):
    create_res = await client.post(
        "/api/v1/schedules",
        json={
            "name": "nightly_cleanup",
            "task_name": "cleanup_expired_sessions",
            "queue": "maintenance",
            "schedule_type": ScheduleType.CRON.value,
            "expression": "0 2 * * *",
        },
    )
    assert create_res.status_code == 201
    schedule_data = create_res.json()
    schedule_id = schedule_data["id"]
    assert schedule_data["name"] == "nightly_cleanup"

    list_res = await client.get("/api/v1/schedules")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    delete_res = await client.delete(f"/api/v1/schedules/{schedule_id}")
    assert delete_res.status_code == 204

    delete_again = await client.delete(f"/api/v1/schedules/{schedule_id}")
    assert delete_again.status_code == 404


@pytest.mark.asyncio
async def test_api_create_schedule_invalid_expression(client: AsyncClient):
    response = await client.post(
        "/api/v1/schedules",
        json={
            "name": "broken_schedule",
            "task_name": "send_email",
            "schedule_type": ScheduleType.CRON.value,
            "expression": "invalid-cron-format",
        },
    )
    assert response.status_code == 400
    assert "Invalid schedule expression" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "TaskForge"
    assert "version" in data
