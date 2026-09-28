from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field


class CleanContext(BaseModel):
    modifications: dict[str, int] = Field(default_factory=dict)
    quarantined_rows: list[dict[str, Any]] = Field(default_factory=list)
    quarantine_reasons: dict[str, int] = Field(default_factory=dict)
    dropped_duplicates: int = 0
    imputed_values: int = 0
    outliers_handled: int = 0

    def record_modification(self, column: str, count: int = 1) -> None:
        self.modifications[column] = self.modifications.get(column, 0) + count

    def quarantine(self, row: dict[str, Any], reason: str) -> None:
        quarantine_entry = dict(row)
        quarantine_entry["_quarantine_reason"] = reason
        self.quarantined_rows.append(quarantine_entry)
        self.quarantine_reasons[reason] = self.quarantine_reasons.get(reason, 0) + 1

    def record_duplicate(self, count: int = 1) -> None:
        self.dropped_duplicates += count

    def record_imputation(self, count: int = 1) -> None:
        self.imputed_values += count

    def record_outlier(self, count: int = 1) -> None:
        self.outliers_handled += count


class BaseCleaner(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        pass
