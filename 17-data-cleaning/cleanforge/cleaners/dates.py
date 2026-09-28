from datetime import datetime
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext

DEFAULT_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%SZ",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%d %B %Y",
]


class DateCleaner(BaseCleaner):
    def __init__(
        self,
        columns: list[str],
        target_format: str = "%Y-%m-%d",
        input_formats: list[str] | None = None,
        fill_on_error: str | None = None,
    ) -> None:
        self.columns = columns
        self.target_format = target_format
        self.input_formats = input_formats or DEFAULT_DATE_FORMATS
        self.fill_on_error = fill_on_error

    @property
    def name(self) -> str:
        return "DateCleaner"

    def _parse_date(self, val: Any) -> str | None:
        if val is None:
            return self.fill_on_error

        if isinstance(val, datetime):
            return val.strftime(self.target_format)

        val_str = str(val).strip()
        if not val_str:
            return self.fill_on_error

        for fmt in self.input_formats:
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt.strftime(self.target_format)
            except ValueError:
                continue

        try:
            iso_str = val_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime(self.target_format)
        except (ValueError, TypeError):
            pass

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
                    new_v = self._parse_date(old_v)
                    if new_v != old_v:
                        new_r[col] = new_v
                        context.record_modification(col)
            cleaned_rows.append(new_r)
        return cleaned_rows
