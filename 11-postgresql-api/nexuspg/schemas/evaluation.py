from typing import Any, Optional
from pydantic import BaseModel, Field


class EvaluationContext(BaseModel):
    user_id: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EvaluationRequest(BaseModel):
    context: EvaluationContext = Field(default_factory=EvaluationContext)


class FlagEvaluationResult(BaseModel):
    flag_key: str
    enabled: bool
    value: Any
    reason: str
    rule_id: Optional[str] = None


class BulkEvaluationRequest(BaseModel):
    flag_keys: Optional[list[str]] = None
    context: EvaluationContext = Field(default_factory=EvaluationContext)


class BulkEvaluationResponse(BaseModel):
    results: dict[str, FlagEvaluationResult]
