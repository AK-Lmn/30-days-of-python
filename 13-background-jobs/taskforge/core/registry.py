import asyncio
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from taskforge.core.exceptions import TaskNotFoundError
from taskforge.core.executor import ExecutionContext


@dataclass
class TaskDefinition:
    name: str
    handler: Callable[..., Any]
    is_async: bool
    timeout_seconds: float = 60.0
    default_max_retries: int = 3
    default_retry_delay_seconds: float = 5.0
    default_queue: str = "default"
    accepts_context: bool = field(init=False)

    def __post_init__(self) -> None:
        params = inspect.signature(self.handler).parameters
        self.accepts_context = "context" in params or "ctx" in params

    async def execute(self, payload: dict[str, Any], context: ExecutionContext) -> Any:
        call_kwargs = dict(payload)
        if self.accepts_context:
            params = inspect.signature(self.handler).parameters
            if "context" in params:
                call_kwargs["context"] = context
            elif "ctx" in params:
                call_kwargs["ctx"] = context

        if self.is_async:
            return await self.handler(**call_kwargs)
        return await asyncio.to_thread(self.handler, **call_kwargs)


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskDefinition] = {}

    def register(
        self,
        name: str | None = None,
        timeout_seconds: float = 60.0,
        default_max_retries: int = 3,
        default_retry_delay_seconds: float = 5.0,
        default_queue: str = "default",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            task_name = name or fn.__name__
            is_async = inspect.iscoroutinefunction(fn)
            self._tasks[task_name] = TaskDefinition(
                name=task_name,
                handler=fn,
                is_async=is_async,
                timeout_seconds=timeout_seconds,
                default_max_retries=default_max_retries,
                default_retry_delay_seconds=default_retry_delay_seconds,
                default_queue=default_queue,
            )
            return fn

        return decorator

    def get(self, name: str) -> TaskDefinition:
        if name not in self._tasks:
            raise TaskNotFoundError(name)
        return self._tasks[name]

    def list_tasks(self) -> list[str]:
        return sorted(self._tasks.keys())

    def has_task(self, name: str) -> bool:
        return name in self._tasks

    def clear(self) -> None:
        self._tasks.clear()


registry = TaskRegistry()
task = registry.register
