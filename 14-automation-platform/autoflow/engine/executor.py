import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from autoflow.engine.conditions import evaluate_conditions
from autoflow.engine.registry import ActionRegistry, registry as default_registry
from autoflow.engine.templating import render_template_value
from autoflow.models.db_models import Workflow, WorkflowRun
from autoflow.models.enums import RunStatus, StepStatus
from autoflow.repositories.run_repo import RunRepository


class WorkflowExecutor:
    def __init__(self, session: AsyncSession, registry: Optional[ActionRegistry] = None) -> None:
        self.session = session
        self.registry = registry or default_registry
        self.run_repo = RunRepository(session)

    async def execute_workflow(
        self,
        workflow: Workflow,
        trigger_type: str,
        trigger_payload: dict[str, Any],
    ) -> WorkflowRun:
        start_time = time.perf_counter()
        run = await self.run_repo.create_run(
            workflow_id=workflow.id,
            trigger_type=trigger_type,
            trigger_payload=trigger_payload,
        )
        run.status = RunStatus.RUNNING.value
        await self.session.flush()

        context: dict[str, Any] = {
            "trigger": {
                "type": trigger_type,
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
            },
            "event": trigger_payload,
            "steps": {},
        }

        if workflow.conditions:
            matches = evaluate_conditions(workflow.conditions, context)
            if not matches:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                await self.run_repo.update_run(
                    run_id=run.id,
                    status=RunStatus.SKIPPED.value,
                    context_data=context,
                    error_message="Conditions did not match trigger payload",
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                )
                await self.session.commit()
                fresh_run = await self.run_repo.get_run_by_id(run.id)
                return fresh_run or run

        workflow_failed = False
        workflow_error: Optional[str] = None

        steps_sorted = sorted(workflow.steps, key=lambda s: s.step_order)

        for step in steps_sorted:
            action = self.registry.get(step.action_type)
            if not action:
                step_run = await self.run_repo.create_step_run(
                    run_id=run.id,
                    step_id=step.id,
                    step_name=step.step_name,
                    action_type=step.action_type,
                    input_data=step.action_config,
                    attempt=1,
                )
                err_msg = f"Unknown action type: {step.action_type}"
                await self.run_repo.update_step_run(
                    step_run_id=step_run.id,
                    status=StepStatus.FAILED.value,
                    error_message=err_msg,
                    duration_ms=0.0,
                )
                workflow_failed = True
                workflow_error = err_msg
                break

            step_succeeded = False
            max_attempts = step.retry_count + 1

            for attempt in range(1, max_attempts + 1):
                step_start = time.perf_counter()
                rendered_config = render_template_value(step.action_config, context)

                step_run = await self.run_repo.create_step_run(
                    run_id=run.id,
                    step_id=step.id,
                    step_name=step.step_name,
                    action_type=step.action_type,
                    input_data=rendered_config,
                    attempt=attempt,
                )

                try:
                    output = await action.execute(rendered_config, context)
                    step_duration_ms = (time.perf_counter() - step_start) * 1000.0
                    await self.run_repo.update_step_run(
                        step_run_id=step_run.id,
                        status=StepStatus.SUCCESS.value,
                        output_data=output,
                        duration_ms=step_duration_ms,
                    )
                    context["steps"][step.step_name] = output
                    step_succeeded = True
                    break
                except Exception as exc:
                    step_duration_ms = (time.perf_counter() - step_start) * 1000.0
                    err = str(exc)
                    await self.run_repo.update_step_run(
                        step_run_id=step_run.id,
                        status=StepStatus.FAILED.value,
                        error_message=err,
                        duration_ms=step_duration_ms,
                    )
                    if attempt < max_attempts and step.retry_delay_seconds > 0:
                        await asyncio.sleep(step.retry_delay_seconds)
                    else:
                        if not step.continue_on_error:
                            workflow_failed = True
                            workflow_error = f"Step '{step.step_name}' failed: {err}"
                            break

            if workflow_failed:
                break

        total_duration_ms = (time.perf_counter() - start_time) * 1000.0
        final_status = RunStatus.FAILED.value if workflow_failed else RunStatus.COMPLETED.value

        await self.run_repo.update_run(
            run_id=run.id,
            status=final_status,
            context_data=context,
            error_message=workflow_error,
            completed_at=datetime.now(timezone.utc),
            duration_ms=total_duration_ms,
        )
        await self.session.commit()

        fresh_run = await self.run_repo.get_run_by_id(run.id)
        return fresh_run or run
