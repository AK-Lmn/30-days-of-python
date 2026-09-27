import asyncio
from datetime import datetime, timezone
from typing import Callable, Optional
from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession

from autoflow.engine.executor import WorkflowExecutor
from autoflow.models.enums import TriggerType
from autoflow.repositories.workflow_repo import WorkflowRepository


class WorkflowScheduler:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        interval_seconds: float = 2.0,
    ) -> None:
        self.session_factory = session_factory
        self.interval_seconds = interval_seconds
        self._last_runs: dict[str, datetime] = {}
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    async def is_due(self, workflow_id: str, trigger_config: dict, now: datetime) -> bool:
        last_run = self._last_runs.get(workflow_id)

        cron_expr = trigger_config.get("cron")
        if cron_expr:
            try:
                if croniter.match(cron_expr, now):
                    if last_run is None or (now - last_run).total_seconds() >= 55.0:
                        return True
            except Exception:
                pass

        interval = trigger_config.get("interval_seconds")
        if interval is not None:
            try:
                interval_float = float(interval)
                if last_run is None or (now - last_run).total_seconds() >= interval_float:
                    return True
            except (ValueError, TypeError):
                pass

        return False

    async def tick(self) -> list[str]:
        now = datetime.now(timezone.utc)
        triggered_workflow_ids: list[str] = []

        async with self.session_factory() as session:
            repo = WorkflowRepository(session)
            workflows = await repo.get_active_scheduled_workflows()

            for wf in workflows:
                if await self.is_due(wf.id, wf.trigger_config, now):
                    self._last_runs[wf.id] = now
                    triggered_workflow_ids.append(wf.id)
                    executor = WorkflowExecutor(session)
                    payload = {
                        "scheduled_time": now.isoformat(),
                        "trigger": "scheduler",
                    }
                    asyncio.create_task(
                        self._safe_execute(wf.id, payload)
                    )

        return triggered_workflow_ids

    async def _safe_execute(self, workflow_id: str, payload: dict) -> None:
        try:
            async with self.session_factory() as session:
                repo = WorkflowRepository(session)
                wf = await repo.get_by_id(workflow_id)
                if wf and wf.enabled:
                    executor = WorkflowExecutor(session)
                    await executor.execute_workflow(
                        workflow=wf,
                        trigger_type=TriggerType.SCHEDULE.value,
                        trigger_payload=payload,
                    )
        except Exception:
            pass

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self.tick()
            except Exception:
                pass
            await asyncio.sleep(self.interval_seconds)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._running:
            self._running = False
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None
