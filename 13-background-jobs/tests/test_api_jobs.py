import pytest
from httpx import AsyncClient
from taskforge.core.enums import JobStatus
from taskforge.repositories.job_repo import JobRepository


@pytest.mark.asyncio
async def test_api_create_job_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/jobs",
        json={
            "task_name": "send_email",
            "payload": {"to": "user@example.com", "subject": "Test Email"},
            "queue": "notifications",
            "priority": 10,
            "delay_seconds": 0,
            "max_retries": 3,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_name"] == "send_email"
    assert data["queue"] == "notifications"
    assert data["priority"] == 10
    assert data["status"] == JobStatus.PENDING.value
    assert data["retry_count"] == 0
    assert data["progress"] == 0.0


@pytest.mark.asyncio
async def test_api_create_job_with_delay(client: AsyncClient):
    response = await client.post(
        "/api/v1/jobs",
        json={
            "task_name": "generate_report",
            "delay_seconds": 300.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == JobStatus.SCHEDULED.value


@pytest.mark.asyncio
async def test_api_create_job_unregistered_task(client: AsyncClient):
    response = await client.post(
        "/api/v1/jobs",
        json={
            "task_name": "non_existent_special_task",
        },
    )
    assert response.status_code == 400
    assert "is not registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_get_job_detail(client: AsyncClient):
    create_res = await client.post(
        "/api/v1/jobs",
        json={"task_name": "resize_image", "payload": {"source_url": "https://img.com/a.jpg"}},
    )
    job_id = create_res.json()["id"]

    get_res = await client.get(f"/api/v1/jobs/{job_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == job_id
    assert get_res.json()["task_name"] == "resize_image"


@pytest.mark.asyncio
async def test_api_get_job_not_found(client: AsyncClient):
    response = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_list_jobs_and_filter(client: AsyncClient):
    await client.post("/api/v1/jobs", json={"task_name": "send_email", "queue": "emails"})
    await client.post("/api/v1/jobs", json={"task_name": "generate_report", "queue": "reports"})

    list_all = await client.get("/api/v1/jobs")
    assert list_all.status_code == 200
    assert list_all.json()["total"] >= 2

    filter_queue = await client.get("/api/v1/jobs?queue=emails")
    assert filter_queue.status_code == 200
    items = filter_queue.json()["items"]
    assert all(i["queue"] == "emails" for i in items)


@pytest.mark.asyncio
async def test_api_cancel_job(client: AsyncClient):
    create_res = await client.post("/api/v1/jobs", json={"task_name": "send_email"})
    job_id = create_res.json()["id"]

    cancel_res = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == JobStatus.CANCELLED.value

    second_cancel = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert second_cancel.status_code == 400


@pytest.mark.asyncio
async def test_api_retry_job(client: AsyncClient, session_factory):
    create_res = await client.post("/api/v1/jobs", json={"task_name": "send_email"})
    job_id = create_res.json()["id"]

    async with session_factory() as session:
        repo = JobRepository(session)
        await repo.mark_failed(
            job_id=job_id,
            error="Connection timeout",
            traceback=None,
            can_retry=False,
            next_retry_at=None,
        )

    retry_res = await client.post(f"/api/v1/jobs/{job_id}/retry")
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == JobStatus.PENDING.value


@pytest.mark.asyncio
async def test_api_list_registered_tasks(client: AsyncClient):
    response = await client.get("/api/v1/jobs/registered-tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert "send_email" in tasks
    assert "generate_report" in tasks
