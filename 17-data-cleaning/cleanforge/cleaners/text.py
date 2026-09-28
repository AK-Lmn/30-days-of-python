import re
import unicodedata
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext
from cleanforge.cleaners.headers import to_camel_case, to_kebab_case, to_snake_case
from cleanforge.models.types import CasingType


class TextCleaner(BaseCleaner):
    def __init__(
        self,
        columns: list[str] | None = None,
        strip: bool = True,
        collapse_spaces: bool = True,
        casing: CasingType | None = None,
        remove_html: bool = False,
        normalize_unicode: bool = True,
        regex_replace: dict[str, str] | None = None,
    ) -> None:
        self.columns = columns
        self.strip = strip
        self.collapse_spaces = collapse_spaces
        self.casing = casing
        self.remove_html = remove_html
        self.normalize_unicode = normalize_unicode
        self.regex_replace = regex_replace or {}

    @property
    def name(self) -> str:
        return "TextCleaner"

    def _clean_text_value(self, val: str) -> str:
        result = val
        if self.normalize_unicode:
            result = unicodedata.normalize("NFKC", result)

        if self.remove_html:
            result = re.sub(r"<[^>]+>", "", result)

        for pat, repl in self.regex_replace.items():
            result = re.sub(pat, repl, result)

        if self.collapse_spaces:
            result = re.sub(r"[ \t\r\f\v]+", " ", result)

        if self.strip:
            result = result.strip()

        if self.casing == CasingType.LOWER:
            result = result.lower()
        elif self.casing == CasingType.UPPER:
            result = result.upper()
        elif self.casing == CasingType.TITLE:
            result = result.title()
        elif self.casing == CasingType.CAPITALIZE:
            result = result.capitalize()
        elif self.casing == CasingType.SNAKE:
            result = to_snake_case(result)
        elif self.casing == CasingType.CAMEL:
            result = to_camel_case(result)
        elif self.casing == CasingType.KEBAB:
            result = to_kebab_case(result)

        return result

    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        if not rows:
            return rows

        target_columns = self.columns or list(rows[0].keys())

        cleaned_rows: list[dict[str, Any]] = []
        for r in rows:
            new_r = dict(r)
            for col in target_columns:
                val = new_r.get(col)
                if isinstance(val, str):
                    cleaned_val = self._clean_text_value(val)
                    if cleaned_val != val:
                        new_r[col] = cleaned_val
                        context.record_modification(col)
            cleaned_rows.append(new_r)

        return cleaned_rows
