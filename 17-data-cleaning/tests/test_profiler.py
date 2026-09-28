from typing import Any
from cleanforge.models.types import DataType
from cleanforge.profiler.analyzer import DataProfiler
from cleanforge.profiler.metrics import (
    calculate_dataset_health_score,
    compute_column_metrics,
)
from cleanforge.profiler.type_infer import (
    infer_column_type,
    infer_scalar_type,
    is_null_or_empty,
)


def test_is_null_or_empty() -> None:
    assert is_null_or_empty(None) is True
    assert is_null_or_empty("") is True
    assert is_null_or_empty("  ") is True
    assert is_null_or_empty("NA") is True
    assert is_null_or_empty("n/a") is True
    assert is_null_or_empty("null") is True
    assert is_null_or_empty("None") is True
    assert is_null_or_empty("?") is True
    assert is_null_or_empty("-") is True
    assert is_null_or_empty("valid text") is False
    assert is_null_or_empty(0) is False
    assert is_null_or_empty(False) is False


def test_infer_scalar_type() -> None:
    assert infer_scalar_type(123) == DataType.INTEGER
    assert infer_scalar_type("456") == DataType.INTEGER
    assert infer_scalar_type("-789") == DataType.INTEGER
    assert infer_scalar_type(3.14) == DataType.FLOAT
    assert infer_scalar_type("12.34") == DataType.FLOAT
    assert infer_scalar_type("true") == DataType.BOOLEAN
    assert infer_scalar_type(False) == DataType.BOOLEAN
    assert infer_scalar_type("user@test.org") == DataType.EMAIL
    assert infer_scalar_type("https://example.com") == DataType.URL
    assert infer_scalar_type("+15551234567") == DataType.PHONE
    assert infer_scalar_type("(555) 123-4567") == DataType.PHONE
    assert infer_scalar_type("2026-09-28") == DataType.DATE
    assert infer_scalar_type("2026-09-28T12:00:00") == DataType.DATETIME
    assert infer_scalar_type("c9b83e3a-5f5c-4ad1-9efb-33c8ef7820a1") == DataType.UUID
    assert infer_scalar_type("just some words") == DataType.STRING
    assert infer_scalar_type(None) == DataType.EMPTY


def test_infer_column_type() -> None:
    int_col = ["1", "2", "3", "4", "NA"]
    assert infer_column_type(int_col) == DataType.INTEGER

    float_col = ["1.5", "2.8", "3.14", "none"]
    assert infer_column_type(float_col) == DataType.FLOAT

    email_col = ["a@b.com", "c@d.com", "e@f.io", ""]
    assert infer_column_type(email_col) == DataType.EMAIL

    mixed_col = ["1", "abc", "true", "2026-01-01"]
    assert infer_column_type(mixed_col) == DataType.STRING

    empty_col = ["", "NA", "null"]
    assert infer_column_type(empty_col) == DataType.STRING


def test_compute_column_metrics_numeric() -> None:
    values = ["10", "20", "30", "40", ""]
    metrics = compute_column_metrics("age", values, DataType.INTEGER)

    assert metrics.name == "age"
    assert metrics.inferred_type == DataType.INTEGER
    assert metrics.total_count == 5
    assert metrics.null_count == 1
    assert metrics.null_percentage == 20.0
    assert metrics.unique_count == 4
    assert metrics.min_value == 10.0
    assert metrics.max_value == 40.0
    assert metrics.mean == 25.0
    assert metrics.median == 25.0


def test_compute_column_metrics_strings_whitespace() -> None:
    values = ["  apple", "banana  ", "orange", "orange", ""]
    metrics = compute_column_metrics("fruit", values, DataType.STRING)

    assert metrics.whitespace_issues == 2
    assert metrics.unique_count == 3
    assert metrics.mode == "orange"


def test_calculate_dataset_health_score() -> None:
    assert calculate_dataset_health_score(0, 0, {}) == 100.0

    perfect_col = compute_column_metrics("id", ["1", "2", "3"], DataType.INTEGER)
    score = calculate_dataset_health_score(3, 0, {"id": perfect_col})
    assert score == 100.0

    dirty_col = compute_column_metrics(
        "name", ["  a  ", "", "b", "c"], DataType.STRING
    )
    score_dirty = calculate_dataset_health_score(4, 1, {"name": dirty_col})
    assert score_dirty < 100.0


def test_data_profiler(sample_raw_records: list[dict[str, Any]]) -> None:
    profiler = DataProfiler()
    profile = profiler.profile(sample_raw_records)

    assert profile.row_count == 5
    assert profile.duplicate_rows == 1
    assert "Full Name" in profile.columns
    assert "Balance" in profile.columns
    assert profile.health_score > 0.0
    assert profile.health_score <= 100.0
