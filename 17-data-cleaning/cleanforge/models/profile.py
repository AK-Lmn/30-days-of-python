from typing import Any
from pydantic import BaseModel, Field
from cleanforge.models.types import DataType


class ColumnProfile(BaseModel):
    name: str
    inferred_type: DataType
    total_count: int
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    min_value: Any | None = None
    max_value: Any | None = None
    mean: float | None = None
    median: float | None = None
    mode: Any | None = None
    std_dev: float | None = None
    whitespace_issues: int = 0
    sample_values: list[Any] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    duplicate_rows: int
    health_score: float
    columns: dict[str, ColumnProfile] = Field(default_factory=dict)
