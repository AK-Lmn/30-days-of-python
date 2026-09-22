from enum import Enum
from typing import Any
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    TOGGLED = "TOGGLED"
    DELETED = "DELETED"


class AuditLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    flag_key: str
    action: AuditAction
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    diff: dict[str, Any] = Field(default_factory=dict)
