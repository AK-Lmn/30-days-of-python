from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SubscriptionBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_url: str = Field(min_length=1, max_length=2048)
    secret_token: str | None = None
    event_patterns: list[str] = Field(default_factory=lambda: ["*"])
    is_active: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_base_seconds: float = Field(default=2.0, ge=0.1, le=60.0)
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=120.0)


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    name: str | None = None
    target_url: str | None = None
    secret_token: str | None = None
    event_patterns: list[str] | None = None
    is_active: bool | None = None
    max_retries: int | None = Field(default=None, ge=0, le=10)
    backoff_base_seconds: float | None = Field(default=None, ge=0.1, le=60.0)
    timeout_seconds: float | None = Field(default=None, ge=1.0, le=120.0)


class SubscriptionRead(SubscriptionBase):
    id: str
    secret_token: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
