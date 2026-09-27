import pytest
from taskforge.core.exceptions import TaskNotFoundError
from taskforge.core.executor import ExecutionContext
from taskforge.core.registry import TaskRegistry


def test_registry_register_and_get():
    reg = TaskRegistry()

    @reg.register(name="sync_add", timeout_seconds=15.0)
    def add(a: int, b: int) -> int:
        return a + b

    @reg.register(name="async_multiply", timeout_seconds=20.0)
    async def multiply(a: int, b: int) -> int:
        return a * b

    assert reg.has_task("sync_add") is True
    assert reg.has_task("async_multiply") is True
    assert reg.has_task("unknown_task") is False

    sync_task = reg.get("sync_add")
    assert sync_task.name == "sync_add"
    assert sync_task.is_async is False
    assert sync_task.timeout_seconds == 15.0
    assert sync_task.accepts_context is False

    async_task = reg.get("async_multiply")
    assert async_task.name == "async_multiply"
    assert async_task.is_async is True
    assert async_task.timeout_seconds == 20.0


def test_registry_unknown_task_raises():
    reg = TaskRegistry()
    with pytest.raises(TaskNotFoundError):
        reg.get("non_existent_job")


def test_registry_list_tasks():
    reg = TaskRegistry()

    @reg.register(name="beta_task")
    def beta() -> None:
        pass

    @reg.register(name="alpha_task")
    def alpha() -> None:
        pass

    assert reg.list_tasks() == ["alpha_task", "beta_task"]


@pytest.mark.asyncio
async def test_registry_execution_sync_task():
    reg = TaskRegistry()

    @reg.register(name="compute_area")
    def compute_area(width: float, height: float) -> float:
        return width * height

    task_def = reg.get("compute_area")
    ctx = ExecutionContext(
        job_id="test-1",
        task_name="compute_area",
        queue="default",
        retry_count=0,
    )
    result = await task_def.execute({"width": 10.0, "height": 5.0}, ctx)
    assert result == 50.0


@pytest.mark.asyncio
async def test_registry_execution_with_context():
    reg = TaskRegistry()
    progress_recorded = []

    async def dummy_progress(p: float, m: str | None) -> None:
        progress_recorded.append((p, m))

    @reg.register(name="progress_worker")
    async def progress_worker(context: ExecutionContext, step_count: int) -> str:
        for i in range(step_count):
            await context.report_progress((i + 1) * 20.0, f"Step {i + 1}")
        return "done"

    task_def = reg.get("progress_worker")
    assert task_def.accepts_context is True

    ctx = ExecutionContext(
        job_id="test-ctx",
        task_name="progress_worker",
        queue="default",
        retry_count=0,
        progress_callback=dummy_progress,
    )
    result = await task_def.execute({"step_count": 3}, ctx)
    assert result == "done"
    assert len(progress_recorded) == 3
    assert progress_recorded[0] == (20.0, "Step 1")
    assert progress_recorded[2] == (60.0, "Step 3")
