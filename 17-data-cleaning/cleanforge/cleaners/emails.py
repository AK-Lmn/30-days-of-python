import re
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext

EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z0-9\.\-]+$")


class EmailCleaner(BaseCleaner):
    def __init__(
        self,
        columns: list[str],
        lowercase: bool = True,
        action_on_invalid: str = "quarantine",
    ) -> None:
        self.columns = columns
        self.lowercase = lowercase
        self.action_on_invalid = action_on_invalid

    @property
    def name(self) -> str:
        return "EmailCleaner"

    def _is_valid_email(self, val: str) -> bool:
        return bool(EMAIL_REGEX.match(val))

    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        cleaned_rows: list[dict[str, Any]] = []
        for r in rows:
            new_r = dict(r)
            quarantine_row = False
            quarantine_reason = ""

            for col in self.columns:
                if col in new_r:
                    val = new_r[col]
                    if val is None:
                        continue
                    val_str = str(val).strip()
                    if not val_str:
                        continue

                    if self.lowercase:
                        val_str = val_str.lower()

                    if not self._is_valid_email(val_str):
                        if self.action_on_invalid == "quarantine":
                            quarantine_row = True
                            quarantine_reason = (
                                f"Invalid email '{val}' in column '{col}'"
                            )
                            break
                        elif self.action_on_invalid == "nullify":
                            new_r[col] = None
                            context.record_modification(col)
                        else:
                            new_r[col] = val_str
                    else:
                        if new_r[col] != val_str:
                            new_r[col] = val_str
                            context.record_modification(col)

            if quarantine_row:
                context.quarantine(r, quarantine_reason)
            else:
                cleaned_rows.append(new_r)

        return cleaned_rows
