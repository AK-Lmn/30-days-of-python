from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsResponse(BaseModel):
    total_flags: int
    enabled_flags: int
    disabled_flags: int
    total_evaluations: int
    evaluations_by_flag: dict[str, int]
    uptime_seconds: float
