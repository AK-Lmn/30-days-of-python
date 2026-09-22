from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-_]+$")
    name: str = Field(min_length=2, max_length=128)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=128)
    description: Optional[str] = None


class EnvironmentBase(BaseModel):
    key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-_]+$")
    name: str = Field(min_length=2, max_length=128)


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=128)


class EnvironmentResponse(EnvironmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    api_key: str
    created_at: datetime


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    environments: list[EnvironmentResponse] = []
