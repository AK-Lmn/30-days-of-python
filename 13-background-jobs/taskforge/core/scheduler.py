import asyncio
from datetime import datetime, timedelta, timezone
from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taskforge.config import get_settings
from taskforge.core.enums import ScheduleType
from taskforge.database import async_session_factory
from taskforge.models.db_models import utc_now
from taskforge.repositories.job_repo import JobRepository


class Scheduler:
    def __init__(
        self,
        poll_interval: float | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        settings = get_settings()
        self.poll_interval = (
            poll_interval
            if poll_interval is not None
            else settings.scheduler_poll_interval_seconds
        )
        self.session_factory = session_factory or async_session_factory
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                await self.tick()
            except Exception:
                pass
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def tick(self) -> None:
        async with self.session_factory() as session:
            repo = JobRepository(session)
            await repo.promote_scheduled_jobs()
            due_schedules = await repo.get_due_schedules()

            now = utc_now()
            for schedule in due_schedules:
                await repo.create_job(
                    task_name=schedule.task_name,
                    payload=schedule.payload,
                    queue=schedule.queue,
                    priority=schedule.priority,
                    scheduled_at=now,
                )

                next_run_at = self.calculate_next_run(
                    schedule_type=ScheduleType(schedule.schedule_type),
                    expression=schedule.expression,
                    base_time=now,
                )
                await repo.update_schedule_run(
                    schedule_id=schedule.id,
                    last_run_at=now,
                    next_run_at=next_run_at,
                )

    @staticmethod
    def calculate_next_run(
        schedule_type: ScheduleType,
        expression: str,
        base_time: datetime | None = None,
    ) -> datetime:
        base = base_time or utc_now()
        if schedule_type == ScheduleType.INTERVAL:
            seconds = float(expression)
            return base + timedelta(seconds=seconds)
        elif schedule_type == ScheduleType.CRON:
            base_tz = base.astimezone(timezone.utc)
            cron = croniter(expression, base_tz)
            next_ts = cron.get_next(datetime)
            if next_ts.tzinfo is None:
                next_ts = next_ts.replace(tzinfo=timezone.utc)
            return next_ts
        raise ValueError(f"Unsupported schedule type: {schedule_type}")
