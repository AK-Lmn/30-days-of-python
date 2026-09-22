from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class PaginationMeta(BaseModel):
    total: int
    offset: int
    limit: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta
