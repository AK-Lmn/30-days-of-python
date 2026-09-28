import re
from datetime import datetime, timezone
from typing import Any, Callable
from pipeforge.transformers.base import BaseTransformer
from pipeforge.models.record import Record


class StringCleaner(BaseTransformer):
    def __init__(
        self,
        fields: list[str] | None = None,
        strip_whitespace: bool = True,
        collapse_spaces: bool = True,
        empty_to_none: bool = True,
        sentinel_nulls: list[str] | None = None,
    ):
        self.fields = fields
        self.strip_whitespace = strip_whitespace
        self.collapse_spaces = collapse_spaces
        self.empty_to_none = empty_to_none
        self.sentinel_nulls = [s.lower() for s in (sentinel_nulls or ["na", "n/a", "null", "none", "nan", "-"]) ]

    def transform(self, record: Record) -> Record | None:
        target_keys = self.fields if self.fields is not None else list(record.data.keys())
        for key in target_keys:
            if key not in record.data:
                continue
            val = record.data[key]
            if isinstance(val, str):
                cleaned = val
                if self.strip_whitespace:
                    cleaned = cleaned.strip()
                if self.collapse_spaces:
                    cleaned = re.sub(r"\s+", " ", cleaned)
                if self.sentinel_nulls and cleaned.lower() in self.sentinel_nulls:
                    cleaned = None
                elif self.empty_to_none and not cleaned:
                    cleaned = None
                record.data[key] = cleaned
        return record


class CaseNormalizer(BaseTransformer):
    def __init__(self, fields: list[str], mode: str = "lower"):
        self.fields = fields
        self.mode = mode.lower()

    def transform(self, record: Record) -> Record | None:
        for field in self.fields:
            if field in record.data and isinstance(record.data[field], str):
                val: str = record.data[field]
                if self.mode == "lower":
                    record.data[field] = val.lower()
                elif self.mode == "upper":
                    record.data[field] = val.upper()
                elif self.mode == "title":
                    record.data[field] = val.title()
        return record


class DateNormalizer(BaseTransformer):
    COMMON_FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    def __init__(
        self,
        fields: list[str],
        output_format: str = "%Y-%m-%d",
        input_formats: list[str] | None = None,
    ):
        self.fields = fields
        self.output_format = output_format
        self.input_formats = input_formats or self.COMMON_FORMATS

    def _parse_date(self, value: str) -> datetime | None:
        val_str = value.strip()
        for fmt in self.input_formats:
            try:
                return datetime.strptime(val_str, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(val_str)
        except ValueError:
            return None

    def transform(self, record: Record) -> Record | None:
        for field in self.fields:
            if field in record.data and record.data[field] is not None:
                raw_val = record.data[field]
                if isinstance(raw_val, datetime):
                    record.data[field] = raw_val.strftime(self.output_format)
                elif isinstance(raw_val, str) and raw_val.strip():
                    parsed = self._parse_date(raw_val)
                    if parsed is not None:
                        record.data[field] = parsed.strftime(self.output_format)
        return record


class TypeCaster(BaseTransformer):
    def __init__(self, type_mapping: dict[str, type | Callable[[Any], Any]]):
        self.type_mapping = type_mapping

    def _cast_bool(self, val: Any) -> bool:
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        return s in {"true", "1", "yes", "y", "t"}

    def transform(self, record: Record) -> Record | None:
        for field, target_type in self.type_mapping.items():
            if field in record.data and record.data[field] is not None:
                val = record.data[field]
                try:
                    if target_type is bool:
                        record.data[field] = self._cast_bool(val)
                    elif target_type is int:
                        record.data[field] = int(float(str(val).strip()))
                    elif target_type is float:
                        record.data[field] = float(str(val).strip())
                    elif target_type is str:
                        record.data[field] = str(val)
                    elif callable(target_type):
                        record.data[field] = target_type(val)
                except (ValueError, TypeError):
                    pass
        return record
