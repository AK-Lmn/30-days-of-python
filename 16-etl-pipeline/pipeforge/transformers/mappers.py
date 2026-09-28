from typing import Any, Callable
from pipeforge.transformers.base import BaseTransformer
from pipeforge.models.record import Record


class FieldRenamer(BaseTransformer):
    def __init__(self, rename_map: dict[str, str]):
        self.rename_map = rename_map

    def transform(self, record: Record) -> Record | None:
        for old_key, new_key in self.rename_map.items():
            if old_key in record.data:
                record.data[new_key] = record.data.pop(old_key)
        return record


class FieldPicker(BaseTransformer):
    def __init__(self, allowed_fields: list[str]):
        self.allowed_fields = set(allowed_fields)

    def transform(self, record: Record) -> Record | None:
        record.data = {k: v for k, v in record.data.items() if k in self.allowed_fields}
        return record


class FieldRemover(BaseTransformer):
    def __init__(self, dropped_fields: list[str]):
        self.dropped_fields = set(dropped_fields)

    def transform(self, record: Record) -> Record | None:
        for field in self.dropped_fields:
            record.data.pop(field, None)
        return record


class DerivedField(BaseTransformer):
    def __init__(self, field_name: str, expression: Callable[[dict[str, Any]], Any]):
        self.field_name = field_name
        self.expression = expression

    def transform(self, record: Record) -> Record | None:
        try:
            record.data[self.field_name] = self.expression(record.data)
        except Exception:
            record.data[self.field_name] = None
        return record


class ValueMapper(BaseTransformer):
    def __init__(self, field_name: str, mapping: dict[Any, Any], default: Any = None, keep_unmatched: bool = True):
        self.field_name = field_name
        self.mapping = mapping
        self.default = default
        self.keep_unmatched = keep_unmatched

    def transform(self, record: Record) -> Record | None:
        if self.field_name in record.data:
            val = record.data[self.field_name]
            if val in self.mapping:
                record.data[self.field_name] = self.mapping[val]
            elif self.default is not None:
                record.data[self.field_name] = self.default
            elif not self.keep_unmatched:
                record.data[self.field_name] = None
        return record


class RecordFilter(BaseTransformer):
    def __init__(self, predicate: Callable[[Record], bool]):
        self.predicate = predicate

    def transform(self, record: Record) -> Record | None:
        if not self.predicate(record):
            record.mark_skipped()
            return None
        return record
