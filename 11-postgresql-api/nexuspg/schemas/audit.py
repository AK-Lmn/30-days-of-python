from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    entity_type: str
    entity_id: str
    action: str
    actor: str
    changes: Optional[Any] = None
    created_at: datetime
