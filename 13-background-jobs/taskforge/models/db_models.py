from datetime import datetime, timezone
import uuid
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TZDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    queue: Mapped[str] = mapped_column(
        String(50), nullable=False, default="default", index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_delay_seconds: Mapped[float] = mapped_column(
        Float, nullable=False, default=5.0
    )
    timeout_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=60.0)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    progress_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utc_now, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TZDateTime, nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TZDateTime, nullable=True
    )


class WorkerModel(Base):
    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(100), nullable=False)
    pid: Mapped[int] = mapped_column(Integer, nullable=False)
    queues: Mapped[str] = mapped_column(String(255), nullable=False)
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    current_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    jobs_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utc_now
    )
    started_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utc_now
    )


class ScheduleModel(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    queue: Mapped[str] = mapped_column(String(50), nullable=False, default="default")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    schedule_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="interval"
    )
    expression: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(
        TZDateTime, nullable=True
    )
    next_run_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utc_now
    )
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utc_now
    )
