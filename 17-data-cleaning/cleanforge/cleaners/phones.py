import re
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext


class PhoneCleaner(BaseCleaner):
    def __init__(
        self,
        columns: list[str],
        phone_format: str = "e164",
        default_country_code: str = "1",
        action_on_invalid: str = "nullify",
    ) -> None:
        self.columns = columns
        self.phone_format = phone_format
        self.default_country_code = default_country_code.lstrip("+")
        self.action_on_invalid = action_on_invalid

    @property
    def name(self) -> str:
        return "PhoneCleaner"

    def _format_phone(self, val: Any) -> str | None:
        if val is None:
            return None

        val_str = str(val).strip()
        if not val_str:
            return None

        has_plus = val_str.startswith("+")
        digits = re.sub(r"\D", "", val_str)

        if len(digits) < 7:
            return None if self.action_on_invalid == "nullify" else val_str

        if len(digits) == 10 and not has_plus:
            digits = f"{self.default_country_code}{digits}"

        if self.phone_format == "digits":
            return digits

        if self.phone_format == "us_standard":
            clean_digits = digits
            if len(clean_digits) == 11 and clean_digits.startswith("1"):
                clean_digits = clean_digits[1:]
            if len(clean_digits) == 10:
                area = clean_digits[:3]
                mid = clean_digits[3:6]
                last = clean_digits[6:]
                return f"({area}) {mid}-{last}"
            return f"+{digits}"

        return f"+{digits}"

    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        cleaned_rows: list[dict[str, Any]] = []
        for r in rows:
            new_r = dict(r)
            for col in self.columns:
                if col in new_r:
                    old_v = new_r[col]
                    new_v = self._format_phone(old_v)
                    if new_v != old_v:
                        new_r[col] = new_v
                        context.record_modification(col)
            cleaned_rows.append(new_r)
        return cleaned_rows
