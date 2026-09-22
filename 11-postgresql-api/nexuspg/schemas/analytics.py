from typing import Any
import uuid
from pydantic import BaseModel


class TagDistributionItem(BaseModel):
    tag_name: str
    flag_count: int


class EnvironmentHealthItem(BaseModel):
    environment_key: str
    environment_name: str
    total_flags: int
    enabled_flags: int
    disabled_flags: int
    rule_count: int


class ProjectAnalyticsResponse(BaseModel):
    project_id: uuid.UUID
    project_key: str
    project_name: str
    total_flags: int
    total_environments: int
    flag_types: dict[str, int]
    tag_distribution: list[TagDistributionItem]
    environments_health: list[EnvironmentHealthItem]
