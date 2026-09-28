from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext

DEFAULT_TRUE_STRINGS = {"true", "1", "yes", "y", "t", "enable", "enabled", "on"}
DEFAULT_FALSE_STRINGS = {"false", "0", "no", "n", "f", "disable", "disabled", "off"}


class BooleanCleaner(BaseCleaner):
    def __init__(
        self,
        columns: list[str],
        true_values: list[str] | None = None,
        false_values: list[str] | None = None,
        nullable: bool = True,
        fill_on_error: bool | None = None,
    ) -> None:
        self.columns = columns
        self.true_values = set(
            s.strip().lower() for s in (true_values or DEFAULT_TRUE_STRINGS)
        )
        self.false_values = set(
            s.strip().lower() for s in (false_values or DEFAULT_FALSE_STRINGS)
        )
        self.nullable = nullable
        self.fill_on_error = fill_on_error

    @property
    def name(self) -> str:
        return "BooleanCleaner"

    def _clean_bool(self, val: Any) -> bool | None:
        if val is None:
            return None if self.nullable else False

        if isinstance(val, bool):
            return val

        if isinstance(val, (int, float)):
            if val == 1:
                return True
            if val == 0:
                return False

        val_str = str(val).strip().lower()
        if not val_str:
            return None if self.nullable else False

        if val_str in self.true_values:
            return True
        if val_str in self.false_values:
            return False

        return self.fill_on_error

    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        cleaned_rows: list[dict[str, Any]] = []
        for r in rows:
            new_r = dict(r)
            for col in self.columns:
                if col in new_r:
                    old_v = new_r[col]
                    new_v = self._clean_bool(old_v)
                    if new_v != old_v:
                        new_r[col] = new_v
                        context.record_modification(col)
            cleaned_rows.append(new_r)
        return cleaned_rows
