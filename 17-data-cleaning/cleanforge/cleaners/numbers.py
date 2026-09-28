import re
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext

CURRENCY_SYMBOLS = {"$", "€", "£", "¥", "₹", "₩", "₽", "฿", "¢"}


class NumberCleaner(BaseCleaner):
    def __init__(
        self,
        columns: list[str],
        strip_currency: bool = True,
        remove_commas: bool = True,
        parse_percentage: bool = True,
        target_type: str = "float",
        decimals: int | None = None,
        fill_on_error: float | int | None = None,
    ) -> None:
        self.columns = columns
        self.strip_currency = strip_currency
        self.remove_commas = remove_commas
        self.parse_percentage = parse_percentage
        self.target_type = target_type
        self.decimals = decimals
        self.fill_on_error = fill_on_error

    @property
    def name(self) -> str:
        return "NumberCleaner"

    def _clean_number(self, val: Any) -> float | int | None:
        if val is None:
            return self.fill_on_error

        if isinstance(val, (int, float)):
            num = float(val)
            if self.target_type == "int":
                return int(round(num))
            if self.decimals is not None:
                return round(num, self.decimals)
            return num

        val_str = str(val).strip()
        if not val_str:
            return self.fill_on_error

        is_pct = False
        if self.parse_percentage and val_str.endswith("%"):
            is_pct = True
            val_str = val_str[:-1].strip()

        if self.strip_currency:
            for s in CURRENCY_SYMBOLS:
                val_str = val_str.replace(s, "")
            val_str = val_str.strip()

        if self.remove_commas:
            if "," in val_str and "." in val_str:
                if val_str.rfind(",") > val_str.rfind("."):
                    val_str = val_str.replace(".", "").replace(",", ".")
                else:
                    val_str = val_str.replace(",", "")
            elif "," in val_str:
                parts = val_str.split(",")
                if len(parts) == 2 and len(parts[1]) in (1, 2):
                    val_str = val_str.replace(",", ".")
                else:
                    val_str = val_str.replace(",", "")

        val_str = re.sub(r"[^\d\.\+\-eE]", "", val_str)

        try:
            parsed = float(val_str)
            if is_pct:
                parsed = parsed / 100.0

            if self.target_type == "int":
                return int(round(parsed))

            if self.decimals is not None:
                return round(parsed, self.decimals)

            return parsed
        except ValueError:
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
                    new_v = self._clean_number(old_v)
                    if new_v != old_v:
                        new_r[col] = new_v
                        context.record_modification(col)
            cleaned_rows.append(new_r)
        return cleaned_rows
