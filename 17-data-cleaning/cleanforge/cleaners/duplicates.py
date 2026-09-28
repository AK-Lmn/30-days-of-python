import difflib
import json
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext
from cleanforge.models.types import DuplicateKeep


class DuplicateCleaner(BaseCleaner):
    def __init__(
        self,
        subset: list[str] | None = None,
        keep: DuplicateKeep = DuplicateKeep.FIRST,
        fuzzy: bool = False,
        similarity_threshold: float = 0.85,
        fuzzy_columns: list[str] | None = None,
    ) -> None:
        self.subset = subset
        self.keep = keep
        self.fuzzy = fuzzy
        self.similarity_threshold = similarity_threshold
        self.fuzzy_columns = fuzzy_columns

    @property
    def name(self) -> str:
        return "DuplicateCleaner"

    def _extract_key(self, row: dict[str, Any]) -> str:
        if self.subset:
            available = [k for k in self.subset if k in row]
            if available:
                sub = {k: row.get(k) for k in available}
                return json.dumps(sub, sort_keys=True, default=str)
        return json.dumps(row, sort_keys=True, default=str)

    def _extract_fuzzy_text(self, row: dict[str, Any]) -> str:
        cols = self.fuzzy_columns or self.subset or list(row.keys())
        parts: list[str] = []
        for c in cols:
            val = row.get(c)
            if val is not None and str(val).strip():
                parts.append(str(val).strip().lower())
        return " ".join(parts)

    def _clean_exact(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for r in rows:
            key = self._extract_key(r)
            counts[key] = counts.get(key, 0) + 1

        seen: set[str] = set()
        kept: list[dict[str, Any]] = []

        if self.keep == DuplicateKeep.NONE:
            for r in rows:
                key = self._extract_key(r)
                if counts[key] == 1:
                    kept.append(r)
                else:
                    context.record_duplicate()
            return kept

        target_rows = reversed(rows) if self.keep == DuplicateKeep.LAST else rows
        for r in target_rows:
            key = self._extract_key(r)
            if key not in seen:
                seen.add(key)
                kept.append(r)
            else:
                context.record_duplicate()

        if self.keep == DuplicateKeep.LAST:
            kept.reverse()

        return kept

    def _clean_fuzzy(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        kept: list[dict[str, Any]] = []
        kept_texts: list[str] = []

        for r in rows:
            text = self._extract_fuzzy_text(r)
            if not text:
                kept.append(r)
                continue

            is_dup = False
            for existing_text in kept_texts:
                sim = difflib.SequenceMatcher(None, text, existing_text).ratio()
                if sim >= self.similarity_threshold:
                    is_dup = True
                    break

            if is_dup:
                context.record_duplicate()
            else:
                kept.append(r)
                kept_texts.append(text)

        return kept

    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        if not rows:
            return rows

        exact_cleaned = self._clean_exact(rows, context)
        if not self.fuzzy:
            return exact_cleaned

        return self._clean_fuzzy(exact_cleaned, context)
