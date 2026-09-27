from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from taskforge.core.enums import JobStatus, Priority, ScheduleType


class JobCreate(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    queue: str = Field(default="default", min_length=1, max_length=50)
    priority: int = Field(default=Priority.NORMAL.value, ge=1, le=100)
    delay_seconds: float = Field(default=0.0, ge=0.0)
    scheduled_at: datetime | None = None
    max_retries: int = Field(default=3, ge=0, le=20)
    retry_delay_seconds: float = Field(default=5.0, ge=0.0, le=86400.0)
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=86400.0)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_name: str
    queue: str
    payload: dict[str, Any]
    priority: int
    status: JobStatus
    retry_count: int
    max_retries: int
    retry_delay_seconds: float
    timeout_seconds: float
    progress: float
    progress_message: str | None
    result: Any | None
    error: str | None
    error_traceback: str | None
    worker_id: str | None
    scheduled_at: datetime
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    offset: int
    limit: int


class JobCancelResponse(BaseModel):
    id: str
    status: JobStatus
    message: str


class JobRetryResponse(BaseModel):
    id: str
    status: JobStatus
    message: str


class QueueStats(BaseModel):
    queue: str
    pending: int
    scheduled: int
    running: int
    completed: int
    failed: int
    retrying: int
    cancelled: int
    dead_letter: int
    total: int


class QueueStatsResponse(BaseModel):
    queues: list[QueueStats]
    total_jobs: int


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hostname: str
    pid: int
    queues: list[str]
    concurrency: int
    status: str
    current_job_id: str | None
    jobs_completed: int
    jobs_failed: int
    last_heartbeat_at: datetime
    started_at: datetime


class ScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    task_name: str = Field(..., min_length=1, max_length=100)
    queue: str = Field(default="default", min_length=1, max_length=50)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=Priority.NORMAL.value, ge=1, le=100)
    schedule_type: ScheduleType = ScheduleType.INTERVAL
    expression: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    task_name: str
    queue: str
    payload: dict[str, Any]
    priority: int
    schedule_type: ScheduleType
    expression: str
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    active_workers: int
    pending_jobs: int
