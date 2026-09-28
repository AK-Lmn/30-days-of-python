import uuid
from typing import Any
from pydantic import BaseModel, Field
from pipeforge.models.enums import RecordStatus


class Record(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    row_number: int = 0
    raw_data: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: RecordStatus = RecordStatus.EXTRACTED
    errors: list[str] = Field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], row_number: int = 0, metadata: dict[str, Any] | None = None) -> "Record":
        return cls(
            row_number=row_number,
            raw_data=raw.copy(),
            data=raw.copy(),
            metadata=metadata or {},
            status=RecordStatus.EXTRACTED,
        )

    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.status = RecordStatus.INVALID

    def mark_valid(self) -> None:
        self.status = RecordStatus.VALID

    def mark_transformed(self) -> None:
        self.status = RecordStatus.TRANSFORMED

    def mark_loaded(self) -> None:
        self.status = RecordStatus.LOADED

    def mark_quarantined(self) -> None:
        self.status = RecordStatus.QUARANTINED

    def mark_skipped(self) -> None:
        self.status = RecordStatus.SKIPPED

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
