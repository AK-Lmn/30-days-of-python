import re
from datetime import datetime
from typing import Any
from cleanforge.models.types import DataType

EMAIL_PATTERN = re.compile(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z0-9\.\-]+$")
URL_PATTERN = re.compile(r"^(?:https?|ftp)://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"^\+?[\d\s\-\(\)\.]{7,25}$")
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
]

DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
]

BOOLEAN_STRINGS = {"true", "false", "yes", "no", "t", "f", "y", "n"}


def is_null_or_empty(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        cleaned = val.strip().lower()
        return cleaned in {"", "none", "null", "nan", "n/a", "na", "-", "?"}
    return False


def is_integer(val: str) -> bool:
    if val.startswith("+"):
        return False
    if val.startswith("-"):
        return val[1:].isdigit()
    return val.isdigit()


def is_float(val: str) -> bool:
    try:
        float(val)
        return True
    except ValueError:
        return False


def is_datetime(val: str) -> bool:
    for fmt in DATETIME_FORMATS:
        try:
            datetime.strptime(val, fmt)
            return True
        except ValueError:
            continue
    return False


def is_date(val: str) -> bool:
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(val, fmt)
            return True
        except ValueError:
            continue
    return False


def infer_scalar_type(val: Any) -> DataType:
    if is_null_or_empty(val):
        return DataType.EMPTY

    if isinstance(val, bool):
        return DataType.BOOLEAN

    if isinstance(val, int):
        return DataType.INTEGER

    if isinstance(val, float):
        return DataType.FLOAT

    val_str = str(val).strip()
    lower_str = val_str.lower()

    if lower_str in BOOLEAN_STRINGS:
        return DataType.BOOLEAN

    if UUID_PATTERN.match(val_str):
        return DataType.UUID

    if EMAIL_PATTERN.match(val_str):
        return DataType.EMAIL

    if URL_PATTERN.match(val_str):
        return DataType.URL

    if is_datetime(val_str):
        return DataType.DATETIME

    if is_date(val_str):
        return DataType.DATE

    has_digits = any(char.isdigit() for char in val_str)
    if has_digits and PHONE_PATTERN.match(val_str):
        digit_count = sum(1 for c in val_str if c.isdigit())
        if 7 <= digit_count <= 15:
            if val_str.startswith("+") or any(sep in val_str for sep in ("(", ")", " ")):
                return DataType.PHONE
            if val_str.count("-") >= 2 or val_str.count(".") >= 2:
                return DataType.PHONE

    if is_integer(val_str):
        return DataType.INTEGER

    if is_float(val_str):
        return DataType.FLOAT

    return DataType.STRING


def infer_column_type(values: list[Any]) -> DataType:
    non_null_values = [v for v in values if not is_null_or_empty(v)]
    if not non_null_values:
        return DataType.STRING

    type_counts: dict[DataType, int] = {}
    for val in non_null_values:
        scalar_type = infer_scalar_type(val)
        type_counts[scalar_type] = type_counts.get(scalar_type, 0) + 1

    total_valid = len(non_null_values)
    for dtype, count in sorted(type_counts.items(), key=lambda item: item[1], reverse=True):
        if dtype != DataType.EMPTY and count / total_valid >= 0.7:
            return dtype

    return DataType.STRING
