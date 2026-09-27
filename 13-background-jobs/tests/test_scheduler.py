from datetime import datetime, timedelta, timezone
import pytest
from taskforge.core.enums import JobStatus, ScheduleType
from taskforge.core.scheduler import Scheduler
from taskforge.models.db_models import utc_now
from taskforge.repositories.job_repo import JobRepository


def test_scheduler_calculate_next_run_interval():
    base = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)
    next_run = Scheduler.calculate_next_run(
        schedule_type=ScheduleType.INTERVAL,
        expression="120",
        base_time=base,
    )
    assert next_run == base + timedelta(seconds=120)


def test_scheduler_calculate_next_run_cron():
    base = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)
    next_run = Scheduler.calculate_next_run(
        schedule_type=ScheduleType.CRON,
        expression="*/15 * * * *",
        base_time=base,
    )
    assert next_run == datetime(2026, 9, 24, 12, 15, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_scheduler_promote_scheduled_jobs(session_factory):
    past = utc_now() - timedelta(minutes=5)
    future = utc_now() + timedelta(minutes=10)

    async with session_factory() as session:
        repo = JobRepository(session)
        past_job = await repo.create_job(
            task_name="send_email",
            scheduled_at=past,
        )
        future_job = await repo.create_job(
            task_name="send_email",
            scheduled_at=future,
        )

        assert past_job.status == JobStatus.PENDING.value
        assert future_job.status == JobStatus.SCHEDULED.value

    scheduler = Scheduler(session_factory=session_factory)
    await scheduler.tick()

    async with session_factory() as session:
        repo = JobRepository(session)
        check_future = await repo.get_job(future_job.id)
        assert check_future.status == JobStatus.SCHEDULED.value


@pytest.mark.asyncio
async def test_scheduler_tick_recurring_schedule(session_factory):
    past = utc_now() - timedelta(seconds=10)

    async with session_factory() as session:
        repo = JobRepository(session)
        schedule = await repo.create_schedule(
            name="every_minute_report",
            task_name="generate_report",
            expression="60",
            schedule_type=ScheduleType.INTERVAL,
            next_run_at=past,
        )

    scheduler = Scheduler(session_factory=session_factory)
    await scheduler.tick()

    async with session_factory() as session:
        repo = JobRepository(session)
        jobs, total = await repo.list_jobs(task_name="generate_report")
        assert total == 1
        assert jobs[0].task_name == "generate_report"

        schedules = await repo.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].last_run_at is not None
        assert schedules[0].next_run_at > utc_now()

        deleted = await repo.delete_schedule(schedule.id)
        assert deleted is True
        remaining = await repo.list_schedules()
        assert len(remaining) == 0
