from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

VerificationStrategyType = Literal["none", "token", "hmac_sha256", "github", "stripe"]


class EndpointBase(BaseModel):
    slug: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    secret: str = ""
    verification_strategy: VerificationStrategyType = "none"
    is_active: bool = True


class EndpointCreate(EndpointBase):
    pass


class EndpointUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    secret: str | None = None
    verification_strategy: VerificationStrategyType | None = None
    is_active: bool | None = None


class EndpointRead(EndpointBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
