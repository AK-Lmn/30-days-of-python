from typing import Any
from pipeforge.models.metrics import PipelineMetrics
from pipeforge.models.record import Record


class QualityGate:
    def __init__(
        self,
        max_error_rate: float = 0.10,
        min_records: int = 1,
        max_null_percentage: dict[str, float] | None = None,
        unique_fields: list[str] | None = None,
    ):
        self.max_error_rate = max_error_rate
        self.min_records = min_records
        self.max_null_percentage = max_null_percentage or {}
        self.unique_fields = unique_fields or []

    def evaluate(self, metrics: PipelineMetrics, records: list[Record]) -> tuple[bool, list[str]]:
        violations: list[str] = []

        if metrics.records_read < self.min_records:
            violations.append(
                f"Minimum record count check failed: got {metrics.records_read}, required {self.min_records}"
            )

        if metrics.records_read > 0:
            actual_error_rate = metrics.error_rate
            if actual_error_rate > self.max_error_rate:
                violations.append(
                    f"Error rate check failed: {actual_error_rate:.2%} exceeded maximum allowed {self.max_error_rate:.2%}"
                )

        if records and self.max_null_percentage:
            total_records = len(records)
            for field, max_pct in self.max_null_percentage.items():
                null_count = sum(
                    1 for r in records
                    if r.data.get(field) is None or (isinstance(r.data.get(field), str) and not r.data.get(field).strip())
                )
                null_pct = null_count / total_records
                if null_pct > max_pct:
                    violations.append(
                        f"Null percentage check failed for '{field}': {null_pct:.2%} exceeded threshold {max_pct:.2%}"
                    )

        if records and self.unique_fields:
            for field in self.unique_fields:
                seen_values: set[Any] = set()
                duplicate_count = 0
                for r in records:
                    val = r.data.get(field)
                    if val is not None:
                        if val in seen_values:
                            duplicate_count += 1
                        else:
                            seen_values.add(val)
                if duplicate_count > 0:
                    violations.append(
                        f"Uniqueness check failed for '{field}': found {duplicate_count} duplicate values"
                    )

        passed = len(violations) == 0
        return passed, violations
