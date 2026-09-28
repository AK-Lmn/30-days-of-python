import json
from typing import Any
from pipeforge.transformers.base import BaseTransformer
from pipeforge.models.record import Record


class Deduplicator(BaseTransformer):
    def __init__(self, key_fields: list[str] | None = None):
        self.key_fields = key_fields
        self.seen_keys: set[Any] = set()

    def _extract_key(self, record: Record) -> Any:
        if self.key_fields:
            return tuple(record.data.get(k) for k in self.key_fields)
        return json.dumps(record.data, sort_keys=True, default=str)

    def reset(self) -> None:
        self.seen_keys.clear()

    def transform(self, record: Record) -> Record | None:
        key = self._extract_key(record)
        if key in self.seen_keys:
            record.mark_skipped()
            return None
        self.seen_keys.add(key)
        return record
