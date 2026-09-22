from enum import Enum
from typing import Any, Optional
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field, field_validator


class FlagType(str, Enum):
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"


class Operator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class RuleCondition(BaseModel):
    attribute: str = Field(..., min_length=1)
    operator: Operator
    value: Any


class TargetingRule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(..., min_length=1)
    conditions: list[RuleCondition] = Field(default_factory=list)
    serve_value: Any
    rollout_percentage: Optional[int] = Field(default=None, ge=0, le=100)


class FlagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    flag_type: FlagType = FlagType.BOOLEAN
    enabled: bool = True
    default_value: Any
    rules: list[TargetingRule] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        return sorted(list({tag.strip().lower() for tag in tags if tag.strip()}))


class FlagCreate(FlagBase):
    key: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$")


class FlagUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    enabled: Optional[bool] = None
    default_value: Optional[Any] = None
    rules: Optional[list[TargetingRule]] = None
    tags: Optional[list[str]] = None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: Optional[list[str]]) -> Optional[list[str]]:
        if tags is None:
            return None
        return sorted(list({tag.strip().lower() for tag in tags if tag.strip()}))


class FlagToggleRequest(BaseModel):
    enabled: Optional[bool] = None


class FlagResponse(FlagBase):
    key: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
