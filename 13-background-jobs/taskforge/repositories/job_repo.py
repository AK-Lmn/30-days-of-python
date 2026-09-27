from datetime import datetime, timedelta, timezone
import json
import uuid
from typing import Any
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taskforge.core.enums import JobStatus, ScheduleType
from taskforge.core.exceptions import (
    InvalidJobStateError,
    JobAlreadyCancelledError,
    JobNotFoundError,
    ScheduleNotFoundError,
)
from taskforge.models.db_models import JobModel, ScheduleModel, WorkerModel, utc_now
from taskforge.models.schemas import QueueStats


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_job(
        self,
        task_name: str,
        payload: dict[str, Any] | None = None,
        queue: str = "default",
        priority: int = 5,
        scheduled_at: datetime | None = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 5.0,
        timeout_seconds: float = 60.0,
    ) -> JobModel:
        now = utc_now()
        effective_scheduled_at = scheduled_at or now
        initial_status = (
            JobStatus.SCHEDULED.value
            if effective_scheduled_at > now
            else JobStatus.PENDING.value
        )

        job = JobModel(
            id=str(uuid.uuid4()),
            task_name=task_name,
            queue=queue,
            payload=payload or {},
            priority=priority,
            status=initial_status,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            timeout_seconds=timeout_seconds,
            scheduled_at=effective_scheduled_at,
            created_at=now,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: str) -> JobModel | None:
        statement = select(JobModel).where(JobModel.id == job_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def claim_next_job(
        self, worker_id: str, queues: list[str]
    ) -> JobModel | None:
        now = utc_now()
        statement = (
            select(JobModel)
            .where(
                JobModel.queue.in_(queues),
                JobModel.status.in_([JobStatus.PENDING.value, JobStatus.RETRYING.value]),
                JobModel.scheduled_at <= now,
            )
            .order_by(JobModel.priority.desc(), JobModel.scheduled_at.asc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        job = result.scalar_one_or_none()
        if not job:
            return None

        job.status = JobStatus.RUNNING.value
        job.worker_id = worker_id
        job.started_at = now
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def update_progress(
        self, job_id: str, progress: float, message: str | None = None
    ) -> None:
        statement = (
            update(JobModel)
            .where(JobModel.id == job_id)
            .values(
                progress=progress,
                progress_message=message,
            )
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def mark_completed(self, job_id: str, result: Any) -> None:
        now = utc_now()
        statement = (
            update(JobModel)
            .where(JobModel.id == job_id)
            .values(
                status=JobStatus.COMPLETED.value,
                progress=100.0,
                result=result,
                error=None,
                error_traceback=None,
                completed_at=now,
            )
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def mark_failed(
        self,
        job_id: str,
        error: str,
        traceback: str | None,
        can_retry: bool,
        next_retry_at: datetime | None,
    ) -> JobStatus:
        now = utc_now()
        job = await self.get_job(job_id)
        if not job:
            return JobStatus.FAILED

        if can_retry and next_retry_at:
            job.status = JobStatus.RETRYING.value
            job.retry_count += 1
            job.scheduled_at = next_retry_at
            job.error = error
            job.error_traceback = traceback
            await self.session.commit()
            return JobStatus.RETRYING

        new_status = (
            JobStatus.DEAD_LETTER.value
            if job.retry_count >= job.max_retries and job.max_retries > 0
            else JobStatus.FAILED.value
        )
        job.status = new_status
        job.error = error
        job.error_traceback = traceback
        job.completed_at = now
        await self.session.commit()
        return JobStatus(new_status)

    async def cancel_job(self, job_id: str) -> JobModel:
        job = await self.get_job(job_id)
        if not job:
            raise JobNotFoundError(job_id)
        if job.status == JobStatus.CANCELLED.value:
            raise JobAlreadyCancelledError(job_id)
        if job.status == JobStatus.COMPLETED.value:
            raise InvalidJobStateError(job_id, job.status, "cancel")

        job.status = JobStatus.CANCELLED.value
        job.completed_at = utc_now()
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def retry_job(self, job_id: str) -> JobModel:
        job = await self.get_job(job_id)
        if not job:
            raise JobNotFoundError(job_id)
        if job.status not in (
            JobStatus.FAILED.value,
            JobStatus.DEAD_LETTER.value,
            JobStatus.CANCELLED.value,
        ):
            raise InvalidJobStateError(job_id, job.status, "retry")

        job.status = JobStatus.PENDING.value
        job.scheduled_at = utc_now()
        job.started_at = None
        job.completed_at = None
        job.error = None
        job.error_traceback = None
        job.progress = 0.0
        job.progress_message = None
        job.retry_count = 0
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def list_jobs(
        self,
        queue: str | None = None,
        status: JobStatus | None = None,
        task_name: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[JobModel], int]:
        filters = []
        if queue:
            filters.append(JobModel.queue == queue)
        if status:
            filters.append(JobModel.status == status.value)
        if task_name:
            filters.append(JobModel.task_name == task_name)

        count_statement = select(func.count(JobModel.id))
        if filters:
            count_statement = count_statement.where(*filters)
        total_result = await self.session.execute(count_statement)
        total = total_result.scalar_one()

        statement = select(JobModel)
        if filters:
            statement = statement.where(*filters)
        statement = (
            statement.order_by(JobModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        items = list(result.scalars().all())
        return items, total

    async def get_queue_stats(self) -> list[QueueStats]:
        statement = select(
            JobModel.queue,
            JobModel.status,
            func.count(JobModel.id),
        ).group_by(JobModel.queue, JobModel.status)
        result = await self.session.execute(statement)

        grouped: dict[str, dict[str, int]] = {}
        for queue, status_str, count in result.all():
            if queue not in grouped:
                grouped[queue] = {s.value: 0 for s in JobStatus}
            grouped[queue][status_str] = count

        stats_list: list[QueueStats] = []
        for queue, counts in grouped.items():
            total = sum(counts.values())
            stats_list.append(
                QueueStats(
                    queue=queue,
                    pending=counts.get(JobStatus.PENDING.value, 0),
                    scheduled=counts.get(JobStatus.SCHEDULED.value, 0),
                    running=counts.get(JobStatus.RUNNING.value, 0),
                    completed=counts.get(JobStatus.COMPLETED.value, 0),
                    failed=counts.get(JobStatus.FAILED.value, 0),
                    retrying=counts.get(JobStatus.RETRYING.value, 0),
                    cancelled=counts.get(JobStatus.CANCELLED.value, 0),
                    dead_letter=counts.get(JobStatus.DEAD_LETTER.value, 0),
                    total=total,
                )
            )
        return stats_list

    async def promote_scheduled_jobs(self) -> int:
        now = utc_now()
        statement = (
            update(JobModel)
            .where(
                JobModel.status == JobStatus.SCHEDULED.value,
                JobModel.scheduled_at <= now,
            )
            .values(status=JobStatus.PENDING.value)
        )
        result = await self.session.execute(statement)
        await self.session.commit()
        return result.rowcount

    async def register_worker_heartbeat(
        self,
        worker_id: str,
        hostname: str,
        pid: int,
        queues: list[str],
        concurrency: int,
        current_job_id: str | None = None,
        status: str = "active",
    ) -> WorkerModel:
        now = utc_now()
        statement = select(WorkerModel).where(WorkerModel.id == worker_id)
        result = await self.session.execute(statement)
        worker = result.scalar_one_or_none()

        queues_str = ",".join(queues)
        if worker:
            worker.last_heartbeat_at = now
            worker.current_job_id = current_job_id
            worker.status = status
            worker.queues = queues_str
            worker.concurrency = concurrency
        else:
            worker = WorkerModel(
                id=worker_id,
                hostname=hostname,
                pid=pid,
                queues=queues_str,
                concurrency=concurrency,
                status=status,
                current_job_id=current_job_id,
                last_heartbeat_at=now,
                started_at=now,
            )
            self.session.add(worker)

        await self.session.commit()
        await self.session.refresh(worker)
        return worker

    async def update_worker_metrics(
        self, worker_id: str, completed_delta: int = 0, failed_delta: int = 0
    ) -> None:
        statement = (
            update(WorkerModel)
            .where(WorkerModel.id == worker_id)
            .values(
                jobs_completed=WorkerModel.jobs_completed + completed_delta,
                jobs_failed=WorkerModel.jobs_failed + failed_delta,
            )
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def list_workers(self, active_within_seconds: float = 30.0) -> list[WorkerModel]:
        cutoff = utc_now() - timedelta(seconds=active_within_seconds)
        statement = (
            select(WorkerModel)
            .where(
                WorkerModel.last_heartbeat_at >= cutoff,
                WorkerModel.status == "active",
            )
            .order_by(WorkerModel.started_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_schedule(
        self,
        name: str,
        task_name: str,
        expression: str,
        queue: str = "default",
        payload: dict[str, Any] | None = None,
        priority: int = 5,
        schedule_type: ScheduleType = ScheduleType.INTERVAL,
        next_run_at: datetime | None = None,
    ) -> ScheduleModel:
        now = utc_now()
        effective_next_run = next_run_at or now
        schedule = ScheduleModel(
            id=str(uuid.uuid4()),
            name=name,
            task_name=task_name,
            queue=queue,
            payload=payload or {},
            priority=priority,
            schedule_type=schedule_type.value,
            expression=expression,
            enabled=True,
            next_run_at=effective_next_run,
            created_at=now,
        )
        self.session.add(schedule)
        await self.session.commit()
        await self.session.refresh(schedule)
        return schedule

    async def get_due_schedules(self) -> list[ScheduleModel]:
        now = utc_now()
        statement = select(ScheduleModel).where(
            ScheduleModel.enabled == True,
            ScheduleModel.next_run_at <= now,
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_schedule_run(
        self, schedule_id: str, last_run_at: datetime, next_run_at: datetime
    ) -> None:
        statement = (
            update(ScheduleModel)
            .where(ScheduleModel.id == schedule_id)
            .values(
                last_run_at=last_run_at,
                next_run_at=next_run_at,
            )
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def list_schedules(self) -> list[ScheduleModel]:
        statement = select(ScheduleModel).order_by(ScheduleModel.created_at.desc())
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def delete_schedule(self, schedule_id: str) -> bool:
        statement = delete(ScheduleModel).where(ScheduleModel.id == schedule_id)
        result = await self.session.execute(statement)
        await self.session.commit()
        return result.rowcount > 0
