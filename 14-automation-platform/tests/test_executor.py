import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from autoflow.engine.executor import WorkflowExecutor
from autoflow.engine.registry import ActionRegistry
from autoflow.models.enums import ActionType, ComparisonOperator, RunStatus, StepStatus, TriggerType
from autoflow.models.schemas import ConditionSchema, StepCreate, WorkflowCreate
from autoflow.repositories.workflow_repo import WorkflowRepository


@pytest.mark.asyncio
async def test_workflow_executor_success_chain(db_session: AsyncSession):
    repo = WorkflowRepository(db_session)
    wf_schema = WorkflowCreate(
        name="Data Processing Pipeline",
        description="Transforms data and notifies",
        enabled=True,
        trigger_type=TriggerType.MANUAL,
        steps=[
            StepCreate(
                step_order=0,
                step_name="transform_step",
                action_type=ActionType.TRANSFORM.value,
                action_config={
                    "mapping": {
                        "user_upper": "{{ event.username | upper }}",
                        "user_id": "{{ event.id }}",
                    }
                },
            ),
            StepCreate(
                step_order=1,
                step_name="notify_step",
                action_type=ActionType.NOTIFICATION.value,
                action_config={
                    "channel": "console",
                    "recipient": "admin@example.com",
                    "message": "Processed {{ steps.transform_step.result.user_upper }} with ID {{ steps.transform_step.result.user_id }}",
                },
            ),
        ],
    )
    wf = await repo.create(wf_schema)

    executor = WorkflowExecutor(db_session)
    run = await executor.execute_workflow(
        workflow=wf,
        trigger_type=TriggerType.MANUAL.value,
        trigger_payload={"username": "bob", "id": 55},
    )

    assert run.status == RunStatus.COMPLETED.value
    assert len(run.step_runs) == 2
    assert run.step_runs[0].status == StepStatus.SUCCESS.value
    assert run.step_runs[0].output_data["result"]["user_upper"] == "BOB"
    assert run.step_runs[1].status == StepStatus.SUCCESS.value
    assert run.step_runs[1].output_data["message"] == "Processed BOB with ID 55"


@pytest.mark.asyncio
async def test_workflow_executor_condition_mismatch_skips(db_session: AsyncSession):
    repo = WorkflowRepository(db_session)
    wf_schema = WorkflowCreate(
        name="Filtered Workflow",
        enabled=True,
        trigger_type=TriggerType.EVENT,
        conditions=[
            ConditionSchema(
                field="event.amount",
                operator=ComparisonOperator.GREATER_THAN,
                value=100,
            )
        ],
        steps=[
            StepCreate(
                step_order=0,
                step_name="dummy_step",
                action_type=ActionType.NOTIFICATION.value,
                action_config={"recipient": "ops@example.com", "message": "High value"},
            )
        ],
    )
    wf = await repo.create(wf_schema)

    executor = WorkflowExecutor(db_session)
    run = await executor.execute_workflow(
        workflow=wf,
        trigger_type=TriggerType.EVENT.value,
        trigger_payload={"amount": 40},
    )

    assert run.status == RunStatus.SKIPPED.value
    assert "Conditions did not match" in (run.error_message or "")
    assert len(run.step_runs) == 0


@pytest.mark.asyncio
async def test_workflow_executor_retry_and_failure(db_session: AsyncSession):
    repo = WorkflowRepository(db_session)
    wf_schema = WorkflowCreate(
        name="Failing Workflow",
        enabled=True,
        trigger_type=TriggerType.MANUAL,
        steps=[
            StepCreate(
                step_order=0,
                step_name="bad_step",
                action_type=ActionType.HTTP_REQUEST.value,
                action_config={"url": "http://127.0.0.1:1/invalid-endpoint"},
                retry_count=1,
                retry_delay_seconds=0.01,
            )
        ],
    )
    wf = await repo.create(wf_schema)

    executor = WorkflowExecutor(db_session)
    run = await executor.execute_workflow(
        workflow=wf,
        trigger_type=TriggerType.MANUAL.value,
        trigger_payload={},
    )

    assert run.status == RunStatus.FAILED.value
    assert len(run.step_runs) == 2
    assert run.step_runs[0].attempt == 1
    assert run.step_runs[1].attempt == 2
    assert run.step_runs[1].status == StepStatus.FAILED.value


@pytest.mark.asyncio
async def test_workflow_executor_continue_on_error(db_session: AsyncSession):
    repo = WorkflowRepository(db_session)
    wf_schema = WorkflowCreate(
        name="Tolerant Workflow",
        enabled=True,
        trigger_type=TriggerType.MANUAL,
        steps=[
            StepCreate(
                step_order=0,
                step_name="bad_optional_step",
                action_type=ActionType.HTTP_REQUEST.value,
                action_config={"url": "http://127.0.0.1:1/invalid"},
                continue_on_error=True,
            ),
            StepCreate(
                step_order=1,
                step_name="next_step",
                action_type=ActionType.NOTIFICATION.value,
                action_config={"recipient": "dev@example.com", "message": "Recovered"},
            ),
        ],
    )
    wf = await repo.create(wf_schema)

    executor = WorkflowExecutor(db_session)
    run = await executor.execute_workflow(
        workflow=wf,
        trigger_type=TriggerType.MANUAL.value,
        trigger_payload={},
    )

    assert run.status == RunStatus.COMPLETED.value
    assert len(run.step_runs) == 2
    assert run.step_runs[0].status == StepStatus.FAILED.value
    assert run.step_runs[1].status == StepStatus.SUCCESS.value
