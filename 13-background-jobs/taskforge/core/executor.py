from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionContext:
    job_id: str
    task_name: str
    queue: str
    retry_count: int
    progress_callback: Callable[[float, str | None], Awaitable[None]] = field(
        default=lambda p, m: None
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    async def report_progress(self, percent: float, message: str | None = None) -> None:
        clamped = max(0.0, min(100.0, float(percent)))
        if self.progress_callback:
            await self.progress_callback(clamped, message)
