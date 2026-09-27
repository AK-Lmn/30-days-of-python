from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class EventIngestResponse(BaseModel):
    event_id: str
    status: str
    event_type: str
    deliveries_scheduled: int
    is_duplicate: bool = False
    message: str = "Event accepted for processing"


class EventSummary(BaseModel):
    id: str
    endpoint_id: str
    event_type: str
    idempotency_key: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventRead(EventSummary):
    payload: dict[str, Any]
    headers: dict[str, Any]
    raw_body: str

    model_config = ConfigDict(from_attributes=True)
