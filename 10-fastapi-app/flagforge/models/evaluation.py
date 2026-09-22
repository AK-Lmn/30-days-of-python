from typing import Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class EvaluationContext(BaseModel):
    entity_id: str = Field(..., min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)


class EvaluationRequest(BaseModel):
    flag_key: str = Field(..., min_length=1)
    context: EvaluationContext
    default_fallback: Optional[Any] = None


class EvaluationResponse(BaseModel):
    flag_key: str
    value: Any
    enabled: bool
    rule_id: Optional[str] = None
    reason: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BulkEvaluationRequest(BaseModel):
    flag_keys: Optional[list[str]] = None
    context: EvaluationContext


class BulkEvaluationResponse(BaseModel):
    evaluations: dict[str, EvaluationResponse]
    count: int
