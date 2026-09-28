import statistics
from collections import Counter
from typing import Any
from cleanforge.models.profile import ColumnProfile
from cleanforge.models.types import DataType
from cleanforge.profiler.type_infer import is_null_or_empty


def compute_column_metrics(
    name: str,
    values: list[Any],
    inferred_type: DataType,
) -> ColumnProfile:
    total_count = len(values)
    null_count = sum(1 for v in values if is_null_or_empty(v))
    null_percentage = (null_count / total_count * 100.0) if total_count > 0 else 0.0

    valid_values = [v for v in values if not is_null_or_empty(v)]
    string_values = [str(v) for v in valid_values]
    unique_count = len(set(string_values))
    unique_percentage = (
        (unique_count / len(valid_values) * 100.0) if valid_values else 0.0
    )

    whitespace_issues = 0
    for v in valid_values:
        if isinstance(v, str):
            if v != v.strip() or "  " in v:
                whitespace_issues += 1

    min_value: Any | None = None
    max_value: Any | None = None
    mean_val: float | None = None
    median_val: float | None = None
    mode_val: Any | None = None
    std_dev_val: float | None = None

    if inferred_type in [DataType.INTEGER, DataType.FLOAT]:
        numeric_values: list[float] = []
        for v in valid_values:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                continue

        if numeric_values:
            min_value = min(numeric_values)
            max_value = max(numeric_values)
            mean_val = statistics.mean(numeric_values)
            median_val = statistics.median(numeric_values)
            if len(numeric_values) > 1:
                std_dev_val = statistics.stdev(numeric_values)
            counter = Counter(numeric_values)
            mode_val = counter.most_common(1)[0][0]
    else:
        if string_values:
            counter = Counter(string_values)
            mode_val = counter.most_common(1)[0][0]
            min_value = min(string_values)
            max_value = max(string_values)

    sample_values = string_values[:5]

    return ColumnProfile(
        name=name,
        inferred_type=inferred_type,
        total_count=total_count,
        null_count=null_count,
        null_percentage=round(null_percentage, 2),
        unique_count=unique_count,
        unique_percentage=round(unique_percentage, 2),
        min_value=min_value,
        max_value=max_value,
        mean=round(mean_val, 2) if mean_val is not None else None,
        median=round(median_val, 2) if median_val is not None else None,
        mode=mode_val,
        std_dev=round(std_dev_val, 2) if std_dev_val is not None else None,
        whitespace_issues=whitespace_issues,
        sample_values=sample_values,
    )


def calculate_dataset_health_score(
    row_count: int,
    duplicate_rows: int,
    columns: dict[str, ColumnProfile],
) -> float:
    if row_count == 0 or not columns:
        return 100.0

    total_cells = row_count * len(columns)
    total_nulls = sum(col.null_count for col in columns.values())
    total_whitespace_issues = sum(col.whitespace_issues for col in columns.values())

    completeness_score = max(0.0, 1.0 - (total_nulls / total_cells)) * 50.0
    duplicate_ratio = duplicate_rows / row_count if row_count > 0 else 0.0
    uniqueness_score = max(0.0, 1.0 - duplicate_ratio) * 30.0
    cleanliness_ratio = (
        total_whitespace_issues / total_cells if total_cells > 0 else 0.0
    )
    cleanliness_score = max(0.0, 1.0 - cleanliness_ratio) * 20.0

    total_score = completeness_score + uniqueness_score + cleanliness_score
    return round(max(0.0, min(100.0, total_score)), 1)
