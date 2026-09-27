from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class DeliveryAttemptRead(BaseModel):
    id: str
    delivery_id: str
    attempt_number: int
    status_code: int | None
    request_headers: dict[str, Any]
    request_body: str
    response_headers: dict[str, Any] | None
    response_body: str | None
    duration_ms: float
    status: str
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliverySummary(BaseModel):
    id: str
    event_id: str
    subscription_id: str
    status: str
    attempts_count: int
    max_retries: int
    next_retry_at: datetime | None
    last_attempt_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryRead(DeliverySummary):
    attempts: list[DeliveryAttemptRead] = []

    model_config = ConfigDict(from_attributes=True)


class ReplayResponse(BaseModel):
    delivery_id: str
    status: str
    attempt_number: int
    status_code: int | None
    success: bool
    error_message: str | None = None
