from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PipelineMetrics(BaseModel):
    records_read: int = 0
    records_valid: int = 0
    records_invalid: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    records_quarantined: int = 0
    records_skipped: int = 0
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    duration_seconds: float = 0.0

    def finish(self) -> None:
        self.end_time = datetime.now(timezone.utc)
        self.duration_seconds = max(0.0, (self.end_time - self.start_time).total_seconds())

    @property
    def error_rate(self) -> float:
        if self.records_read == 0:
            return 0.0
        return self.records_invalid / self.records_read

    @property
    def throughput_records_per_second(self) -> float:
        if self.duration_seconds <= 0:
            return float(self.records_read)
        return round(self.records_read / self.duration_seconds, 2)
