from typing import Any
from pydantic import BaseModel, Field
from cleanforge.models.types import CasingType, DuplicateKeep, ImputeStrategy, OutlierMethod, OutlierStrategy


class HeadersConfig(BaseModel):
    casing: CasingType | None = None
    strip_whitespace: bool = True
    remove_special_characters: bool = True
    rename: dict[str, str] = Field(default_factory=dict)


class ColumnMissingConfig(BaseModel):
    strategy: ImputeStrategy
    fill_value: Any | None = None


class MissingConfig(BaseModel):
    missing_values: list[str] = Field(
        default_factory=lambda: ["", "na", "n/a", "null", "none", "nan", "-", "?"]
    )
    default_strategy: ImputeStrategy | None = None
    default_fill_value: Any | None = None
    columns: dict[str, ColumnMissingConfig] = Field(default_factory=dict)
    drop_threshold_percent: float | None = None


class DuplicateConfig(BaseModel):
    enabled: bool = True
    subset: list[str] | None = None
    keep: DuplicateKeep = DuplicateKeep.FIRST
    fuzzy: bool = False
    similarity_threshold: float = 0.85
    fuzzy_columns: list[str] | None = None


class TextConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    strip: bool = True
    collapse_spaces: bool = True
    casing: CasingType | None = None
    remove_html: bool = False
    normalize_unicode: bool = True
    regex_replace: dict[str, str] = Field(default_factory=dict)


class NumberConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    strip_currency: bool = True
    remove_commas: bool = True
    parse_percentage: bool = True
    target_type: str = "float"
    decimals: int | None = None
    fill_on_error: float | int | None = None


class DateConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    target_format: str = "%Y-%m-%d"
    input_formats: list[str] = Field(
        default_factory=lambda: [
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
    )
    fill_on_error: str | None = None


class BooleanConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    true_values: list[str] = Field(
        default_factory=lambda: ["true", "1", "yes", "y", "t", "enable", "enabled", "on"]
    )
    false_values: list[str] = Field(
        default_factory=lambda: ["false", "0", "no", "n", "f", "disable", "disabled", "off"]
    )
    nullable: bool = True


class PhoneConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    format: str = "e164"
    default_country_code: str = "1"


class EmailConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    lowercase: bool = True
    action_on_invalid: str = "quarantine"


class OutlierConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    method: OutlierMethod = OutlierMethod.IQR
    strategy: OutlierStrategy = OutlierStrategy.CLIP
    threshold: float = 1.5


class ValidationRule(BaseModel):
    column: str
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: list[Any] | None = None
    regex_pattern: str | None = None
    not_null: bool = False
    action: str = "quarantine"


class RecipeConfig(BaseModel):
    name: str = "default_cleaning_recipe"
    version: str = "1.0"
    headers: HeadersConfig | None = None
    missing: MissingConfig | None = None
    duplicates: DuplicateConfig | None = None
    text: list[TextConfig] = Field(default_factory=list)
    numbers: list[NumberConfig] = Field(default_factory=list)
    dates: list[DateConfig] = Field(default_factory=list)
    booleans: list[BooleanConfig] = Field(default_factory=list)
    phones: list[PhoneConfig] = Field(default_factory=list)
    emails: list[EmailConfig] = Field(default_factory=list)
    outliers: list[OutlierConfig] = Field(default_factory=list)
    validations: list[ValidationRule] = Field(default_factory=list)
