import asyncio
import pytest
from taskforge.core.enums import JobStatus
from taskforge.core.registry import registry
from taskforge.core.worker import Worker
from taskforge.repositories.job_repo import JobRepository


@pytest.mark.asyncio
async def test_worker_priority_claiming(session_factory):
    async with session_factory() as session:
        repo = JobRepository(session)
        low_job = await repo.create_job(
            task_name="send_email",
            payload={"to": "low@example.com", "subject": "Low"},
            priority=1,
        )
        high_job = await repo.create_job(
            task_name="send_email",
            payload={"to": "high@example.com", "subject": "High"},
            priority=10,
        )

        worker = Worker(
            worker_id="test-worker",
            queues=["default"],
            session_factory=session_factory,
        )
        claimed = await repo.claim_next_job(worker.worker_id, ["default"])
        assert claimed is not None
        assert claimed.id == high_job.id
        assert claimed.status == JobStatus.RUNNING.value

        second_claimed = await repo.claim_next_job(worker.worker_id, ["default"])
        assert second_claimed is not None
        assert second_claimed.id == low_job.id


@pytest.mark.asyncio
async def test_worker_successful_execution(session_factory):
    async with session_factory() as session:
        repo = JobRepository(session)
        job = await repo.create_job(
            task_name="send_email",
            payload={"to": "alice@example.com", "subject": "Welcome"},
            queue="default",
        )

    worker = Worker(
        worker_id="w-success",
        queues=["default"],
        session_factory=session_factory,
        poll_interval=0.05,
    )

    await worker._execute_job(job.id)

    async with session_factory() as session:
        repo = JobRepository(session)
        updated = await repo.get_job(job.id)
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED.value
        assert updated.progress == 100.0
        assert updated.result is not None
        assert updated.result["status"] == "delivered"
        assert updated.completed_at is not None
        assert worker.jobs_completed == 1


@pytest.mark.asyncio
async def test_worker_retry_mechanism(session_factory):
    async with session_factory() as session:
        repo = JobRepository(session)
        job = await repo.create_job(
            task_name="failing_task",
            payload={"message": "network timeout simulation"},
            max_retries=2,
            retry_delay_seconds=0.1,
        )

    worker = Worker(
        worker_id="w-retry",
        queues=["default"],
        session_factory=session_factory,
        poll_interval=0.05,
    )

    await worker._execute_job(job.id)

    async with session_factory() as session:
        repo = JobRepository(session)
        updated = await repo.get_job(job.id)
        assert updated is not None
        assert updated.status == JobStatus.RETRYING.value
        assert updated.retry_count == 1
        assert "network timeout simulation" in (updated.error or "")


@pytest.mark.asyncio
async def test_worker_dead_letter_after_max_retries(session_factory):
    async with session_factory() as session:
        repo = JobRepository(session)
        job = await repo.create_job(
            task_name="failing_task",
            payload={"message": "fatal error"},
            max_retries=1,
            retry_delay_seconds=0.05,
        )

    worker = Worker(
        worker_id="w-dead-letter",
        queues=["default"],
        session_factory=session_factory,
        poll_interval=0.05,
    )

    await worker._execute_job(job.id)

    async with session_factory() as session:
        repo = JobRepository(session)
        first_attempt = await repo.get_job(job.id)
        assert first_attempt.status == JobStatus.RETRYING.value
        assert first_attempt.retry_count == 1

    await worker._execute_job(job.id)

    async with session_factory() as session:
        repo = JobRepository(session)
        final_job = await repo.get_job(job.id)
        assert final_job.status == JobStatus.DEAD_LETTER.value
        assert final_job.completed_at is not None


@pytest.mark.asyncio
async def test_worker_timeout(session_factory):
    async with session_factory() as session:
        repo = JobRepository(session)
        job = await repo.create_job(
            task_name="slow_task",
            payload={"duration": 1.0},
            timeout_seconds=0.05,
            max_retries=0,
        )

    worker = Worker(
        worker_id="w-timeout",
        queues=["default"],
        session_factory=session_factory,
    )

    await worker._execute_job(job.id)

    async with session_factory() as session:
        repo = JobRepository(session)
        failed_job = await repo.get_job(job.id)
        assert failed_job is not None
        assert failed_job.status == JobStatus.FAILED.value
        assert "timed out after" in (failed_job.error or "")


@pytest.mark.asyncio
async def test_worker_heartbeat_and_metrics(session_factory):
    worker = Worker(
        worker_id="w-heartbeat-test",
        queues=["default", "critical"],
        concurrency=4,
        session_factory=session_factory,
    )

    async with session_factory() as session:
        repo = JobRepository(session)
        await repo.register_worker_heartbeat(
            worker_id=worker.worker_id,
            hostname=worker.hostname,
            pid=worker.pid,
            queues=worker.queues,
            concurrency=worker.concurrency,
        )
        workers = await repo.list_workers()
        assert len(workers) == 1
        assert workers[0].id == worker.worker_id
        assert workers[0].concurrency == 4

        await repo.update_worker_metrics(worker.worker_id, completed_delta=5, failed_delta=1)
        updated_workers = await repo.list_workers()
        assert updated_workers[0].jobs_completed == 5
        assert updated_workers[0].jobs_failed == 1
