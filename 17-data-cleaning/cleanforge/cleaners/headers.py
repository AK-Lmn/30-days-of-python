import re
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext
from cleanforge.models.types import CasingType


def to_snake_case(text: str) -> str:
    s = re.sub(r"[-\s]+", "_", text)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    s = re.sub(r"[^0-9a-zA-Z_]", "", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_").lower()


def to_camel_case(text: str) -> str:
    snake = to_snake_case(text)
    components = snake.split("_")
    if not components:
        return ""
    return components[0] + "".join(x.capitalize() for x in components[1:])


def to_kebab_case(text: str) -> str:
    snake = to_snake_case(text)
    return snake.replace("_", "-")


class HeaderCleaner(BaseCleaner):
    def __init__(
        self,
        casing: CasingType | None = CasingType.SNAKE,
        strip_whitespace: bool = True,
        remove_special_characters: bool = True,
        rename_map: dict[str, str] | None = None,
    ) -> None:
        self.casing = casing
        self.strip_whitespace = strip_whitespace
        self.remove_special_characters = remove_special_characters
        self.rename_map = rename_map or {}

    @property
    def name(self) -> str:
        return "HeaderCleaner"

    def _transform_key(self, key: str) -> str:
        if key in self.rename_map:
            return self.rename_map[key]

        transformed = key
        if self.strip_whitespace:
            transformed = transformed.strip()

        if self.remove_special_characters:
            transformed = re.sub(r"[^\w\s-]", "", transformed)

        if self.casing == CasingType.SNAKE:
            transformed = to_snake_case(transformed)
        elif self.casing == CasingType.CAMEL:
            transformed = to_camel_case(transformed)
        elif self.casing == CasingType.KEBAB:
            transformed = to_kebab_case(transformed)
        elif self.casing == CasingType.LOWER:
            transformed = transformed.lower()
        elif self.casing == CasingType.UPPER:
            transformed = transformed.upper()
        elif self.casing == CasingType.TITLE:
            transformed = transformed.title()

        if transformed in self.rename_map:
            return self.rename_map[transformed]

        return transformed or "unnamed_column"

    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        if not rows:
            return rows

        original_keys = list(rows[0].keys())
        key_mapping: dict[str, str] = {}
        seen_transformed: dict[str, int] = {}

        for k in original_keys:
            new_k = self._transform_key(k)
            if new_k in seen_transformed:
                seen_transformed[new_k] += 1
                new_k = f"{new_k}_{seen_transformed[new_k]}"
            else:
                seen_transformed[new_k] = 0
            key_mapping[k] = new_k
            if k != new_k:
                context.record_modification(new_k)

        cleaned_rows: list[dict[str, Any]] = []
        for row in rows:
            new_row = {
                key_mapping.get(k, self._transform_key(k)): v
                for k, v in row.items()
            }
            cleaned_rows.append(new_row)

        return cleaned_rows
