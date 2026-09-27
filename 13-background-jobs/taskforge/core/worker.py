import asyncio
import os
import socket
import traceback
import uuid
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taskforge.config import get_settings
from taskforge.core.enums import JobStatus
from taskforge.core.exceptions import TaskForgeError, TaskNotFoundError, TaskTimeoutError
from taskforge.core.executor import ExecutionContext
from taskforge.core.registry import registry
from taskforge.database import async_session_factory
from taskforge.models.db_models import utc_now
from taskforge.repositories.job_repo import JobRepository


class Worker:
    def __init__(
        self,
        worker_id: str | None = None,
        queues: list[str] | None = None,
        concurrency: int = 2,
        poll_interval: float | None = None,
        heartbeat_interval: float | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        settings = get_settings()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.worker_id = (
            worker_id or f"{self.hostname}-{self.pid}-{uuid.uuid4().hex[:6]}"
        )
        self.queues = queues or [settings.default_queue]
        self.concurrency = max(1, concurrency)
        self.poll_interval = (
            poll_interval
            if poll_interval is not None
            else settings.worker_poll_interval_seconds
        )
        self.heartbeat_interval = (
            heartbeat_interval
            if heartbeat_interval is not None
            else settings.worker_heartbeat_interval_seconds
        )
        self.session_factory = session_factory or async_session_factory

        self._running = False
        self._semaphore = asyncio.Semaphore(self.concurrency)
        self._active_tasks: set[asyncio.Task] = set()
        self._heartbeat_task: asyncio.Task | None = None
        self.jobs_completed = 0
        self.jobs_failed = 0

    async def start(self) -> None:
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        await self._run_loop()

    async def stop(self) -> None:
        self._running = False
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        async with self.session_factory() as session:
            repo = JobRepository(session)
            await repo.register_worker_heartbeat(
                worker_id=self.worker_id,
                hostname=self.hostname,
                pid=self.pid,
                queues=self.queues,
                concurrency=self.concurrency,
                current_job_id=None,
                status="stopped",
            )

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                async with self.session_factory() as session:
                    repo = JobRepository(session)
                    await repo.register_worker_heartbeat(
                        worker_id=self.worker_id,
                        hostname=self.hostname,
                        pid=self.pid,
                        queues=self.queues,
                        concurrency=self.concurrency,
                        status="active",
                    )
            except Exception:
                pass
            await asyncio.sleep(self.heartbeat_interval)

    async def _run_loop(self) -> None:
        while self._running:
            if self._semaphore.locked():
                await asyncio.sleep(self.poll_interval)
                continue

            job = None
            try:
                async with self.session_factory() as session:
                    repo = JobRepository(session)
                    job = await repo.claim_next_job(self.worker_id, self.queues)
            except Exception:
                await asyncio.sleep(self.poll_interval)
                continue

            if not job:
                await asyncio.sleep(self.poll_interval)
                continue

            await self._semaphore.acquire()
            task = asyncio.create_task(self._safe_execute_job(job.id))
            self._active_tasks.add(task)
            task.add_done_callback(self._on_task_done)

    def _on_task_done(self, task: asyncio.Task) -> None:
        self._active_tasks.discard(task)
        self._semaphore.release()

    async def _safe_execute_job(self, job_id: str) -> None:
        try:
            await self._execute_job(job_id)
        except Exception:
            pass

    async def _execute_job(self, job_id: str) -> None:
        async with self.session_factory() as session:
            repo = JobRepository(session)
            job = await repo.get_job(job_id)
            if not job:
                return

            try:
                task_def = registry.get(job.task_name)
            except TaskNotFoundError as exc:
                await repo.mark_failed(
                    job_id=job.id,
                    error=str(exc),
                    traceback=traceback.format_exc(),
                    can_retry=False,
                    next_retry_at=None,
                )
                self.jobs_failed += 1
                await repo.update_worker_metrics(self.worker_id, failed_delta=1)
                return

        async def progress_reporter(percent: float, message: str | None = None) -> None:
            async with self.session_factory() as prog_session:
                prog_repo = JobRepository(prog_session)
                await prog_repo.update_progress(job_id, percent, message)

        context = ExecutionContext(
            job_id=job.id,
            task_name=job.task_name,
            queue=job.queue,
            retry_count=job.retry_count,
            progress_callback=progress_reporter,
        )

        try:
            result = await asyncio.wait_for(
                task_def.execute(job.payload, context),
                timeout=job.timeout_seconds,
            )
            async with self.session_factory() as done_session:
                done_repo = JobRepository(done_session)
                await done_repo.mark_completed(job.id, result)
                self.jobs_completed += 1
                await done_repo.update_worker_metrics(
                    self.worker_id, completed_delta=1
                )
        except asyncio.TimeoutError:
            timeout_err = TaskTimeoutError(job.id, job.timeout_seconds)
            await self._handle_failure(
                job_id=job.id,
                error=str(timeout_err),
                tb=traceback.format_exc(),
                retry_count=job.retry_count,
                max_retries=job.max_retries,
                retry_delay_seconds=job.retry_delay_seconds,
            )
        except Exception as exc:
            await self._handle_failure(
                job_id=job.id,
                error=f"{type(exc).__name__}: {str(exc)}",
                tb=traceback.format_exc(),
                retry_count=job.retry_count,
                max_retries=job.max_retries,
                retry_delay_seconds=job.retry_delay_seconds,
            )

    async def _handle_failure(
        self,
        job_id: str,
        error: str,
        tb: str,
        retry_count: int,
        max_retries: int,
        retry_delay_seconds: float,
    ) -> None:
        can_retry = retry_count < max_retries
        next_retry_at = None
        if can_retry:
            backoff = retry_delay_seconds * (2**retry_count)
            next_retry_at = utc_now() + timedelta(seconds=backoff)

        async with self.session_factory() as fail_session:
            fail_repo = JobRepository(fail_session)
            await fail_repo.mark_failed(
                job_id=job_id,
                error=error,
                traceback=tb,
                can_retry=can_retry,
                next_retry_at=next_retry_at,
            )
            self.jobs_failed += 1
            await fail_repo.update_worker_metrics(self.worker_id, failed_delta=1)
