from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str = Field(default="#4f46e5", max_length=32)


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class RuleConditionBase(BaseModel):
    attribute: str = Field(min_length=1, max_length=64)
    operator: str = Field(min_length=1, max_length=32)
    values: Any


class RuleConditionCreate(RuleConditionBase):
    pass


class RuleConditionResponse(RuleConditionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_id: uuid.UUID


class TargetingRuleBase(BaseModel):
    priority: int = 0
    name: str = Field(min_length=1, max_length=128)
    serve_value: Any
    percentage: int = Field(default=100, ge=0, le=100)


class TargetingRuleCreate(TargetingRuleBase):
    conditions: list[RuleConditionCreate] = []


class TargetingRuleResponse(TargetingRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    flag_environment_id: uuid.UUID
    created_at: datetime
    conditions: list[RuleConditionResponse] = []


class FlagEnvironmentStateUpdate(BaseModel):
    enabled: Optional[bool] = None
    percentage: Optional[int] = Field(default=None, ge=0, le=100)
    variant_value: Optional[Any] = None
    rules: Optional[list[TargetingRuleCreate]] = None


class FlagEnvironmentStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    flag_id: uuid.UUID
    environment_id: uuid.UUID
    enabled: bool
    percentage: int
    variant_value: Optional[Any] = None
    updated_at: datetime
    rules: list[TargetingRuleResponse] = []


class FlagBase(BaseModel):
    key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-_]+$")
    name: str = Field(min_length=2, max_length=128)
    description: Optional[str] = None
    flag_type: str = Field(default="boolean", pattern=r"^(boolean|string|numeric|json)$")
    default_value: Any = False


class FlagCreate(FlagBase):
    tags: list[str] = []


class FlagUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=128)
    description: Optional[str] = None
    default_value: Optional[Any] = None
    tags: Optional[list[str]] = None


class FlagResponse(FlagBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    tags: list[TagResponse] = []


class FlagDetailResponse(FlagResponse):
    flag_states: list[FlagEnvironmentStateResponse] = []
