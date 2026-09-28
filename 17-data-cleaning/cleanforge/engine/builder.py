from pathlib import Path
from typing import Any
from cleanforge.cleaners.base import BaseCleaner
from cleanforge.cleaners.booleans import BooleanCleaner
from cleanforge.cleaners.dates import DateCleaner
from cleanforge.cleaners.duplicates import DuplicateCleaner
from cleanforge.cleaners.emails import EmailCleaner
from cleanforge.cleaners.headers import HeaderCleaner
from cleanforge.cleaners.missing import MissingCleaner
from cleanforge.cleaners.numbers import NumberCleaner
from cleanforge.cleaners.outliers import OutlierCleaner
from cleanforge.cleaners.phones import PhoneCleaner
from cleanforge.cleaners.text import TextCleaner
from cleanforge.cleaners.validator import ValidationCleaner
from cleanforge.engine.pipeline import CleanEngine
from cleanforge.io.reader import DatasetReader
from cleanforge.io.writer import DatasetWriter
from cleanforge.models.recipe import RecipeConfig, ValidationRule
from cleanforge.models.report import CleanReport
from cleanforge.models.types import (
    CasingType,
    DuplicateKeep,
    ImputeStrategy,
    OutlierMethod,
    OutlierStrategy,
)


class CleanBuilder:
    def __init__(self) -> None:
        self.raw_data: list[dict[str, Any]] = []
        self.cleaners: list[BaseCleaner] = []
        self.reader = DatasetReader()
        self.writer = DatasetWriter()

    def load(self, file_path: str | Path, **kwargs: Any) -> "CleanBuilder":
        self.raw_data = self.reader.read(file_path, **kwargs)
        return self

    def from_records(self, records: list[dict[str, Any]]) -> "CleanBuilder":
        self.raw_data = [dict(r) for r in records]
        return self

    def standardize_headers(
        self,
        casing: CasingType | None = CasingType.SNAKE,
        strip_whitespace: bool = True,
        remove_special_characters: bool = True,
        rename_map: dict[str, str] | None = None,
    ) -> "CleanBuilder":
        self.cleaners.append(
            HeaderCleaner(
                casing=casing,
                strip_whitespace=strip_whitespace,
                remove_special_characters=remove_special_characters,
                rename_map=rename_map,
            )
        )
        return self

    def handle_missing(
        self,
        missing_markers: list[str] | None = None,
        default_strategy: ImputeStrategy | None = None,
        default_fill_value: Any | None = None,
        column_strategies: dict[str, tuple[ImputeStrategy, Any | None]] | None = None,
        drop_threshold_percent: float | None = None,
    ) -> "CleanBuilder":
        self.cleaners.append(
            MissingCleaner(
                missing_markers=missing_markers,
                default_strategy=default_strategy,
                default_fill_value=default_fill_value,
                column_strategies=column_strategies,
                drop_threshold_percent=drop_threshold_percent,
            )
        )
        return self

    def drop_duplicates(
        self,
        subset: list[str] | None = None,
        keep: DuplicateKeep = DuplicateKeep.FIRST,
        fuzzy: bool = False,
        similarity_threshold: float = 0.85,
        fuzzy_columns: list[str] | None = None,
    ) -> "CleanBuilder":
        self.cleaners.append(
            DuplicateCleaner(
                subset=subset,
                keep=keep,
                fuzzy=fuzzy,
                similarity_threshold=similarity_threshold,
                fuzzy_columns=fuzzy_columns,
            )
        )
        return self

    def clean_text(
        self,
        columns: list[str] | None = None,
        strip: bool = True,
        collapse_spaces: bool = True,
        casing: CasingType | None = None,
        remove_html: bool = False,
        normalize_unicode: bool = True,
        regex_replace: dict[str, str] | None = None,
    ) -> "CleanBuilder":
        self.cleaners.append(
            TextCleaner(
                columns=columns,
                strip=strip,
                collapse_spaces=collapse_spaces,
                casing=casing,
                remove_html=remove_html,
                normalize_unicode=normalize_unicode,
                regex_replace=regex_replace,
            )
        )
        return self

    def clean_numbers(
        self,
        columns: list[str],
        strip_currency: bool = True,
        remove_commas: bool = True,
        parse_percentage: bool = True,
        target_type: str = "float",
        decimals: int | None = None,
        fill_on_error: float | int | None = None,
    ) -> "CleanBuilder":
        self.cleaners.append(
            NumberCleaner(
                columns=columns,
                strip_currency=strip_currency,
                remove_commas=remove_commas,
                parse_percentage=parse_percentage,
                target_type=target_type,
                decimals=decimals,
                fill_on_error=fill_on_error,
            )
        )
        return self

    def clean_dates(
        self,
        columns: list[str],
        target_format: str = "%Y-%m-%d",
        input_formats: list[str] | None = None,
        fill_on_error: str | None = None,
    ) -> "CleanBuilder":
        self.cleaners.append(
            DateCleaner(
                columns=columns,
                target_format=target_format,
                input_formats=input_formats,
                fill_on_error=fill_on_error,
            )
        )
        return self

    def clean_booleans(
        self,
        columns: list[str],
        true_values: list[str] | None = None,
        false_values: list[str] | None = None,
        nullable: bool = True,
        fill_on_error: bool | None = None,
    ) -> "CleanBuilder":
        self.cleaners.append(
            BooleanCleaner(
                columns=columns,
                true_values=true_values,
                false_values=false_values,
                nullable=nullable,
                fill_on_error=fill_on_error,
            )
        )
        return self

    def clean_phones(
        self,
        columns: list[str],
        phone_format: str = "e164",
        default_country_code: str = "1",
    ) -> "CleanBuilder":
        self.cleaners.append(
            PhoneCleaner(
                columns=columns,
                phone_format=phone_format,
                default_country_code=default_country_code,
            )
        )
        return self

    def clean_emails(
        self,
        columns: list[str],
        lowercase: bool = True,
        action_on_invalid: str = "quarantine",
    ) -> "CleanBuilder":
        self.cleaners.append(
            EmailCleaner(
                columns=columns,
                lowercase=lowercase,
                action_on_invalid=action_on_invalid,
            )
        )
        return self

    def handle_outliers(
        self,
        columns: list[str],
        method: OutlierMethod = OutlierMethod.IQR,
        strategy: OutlierStrategy = OutlierStrategy.CLIP,
        threshold: float = 1.5,
    ) -> "CleanBuilder":
        self.cleaners.append(
            OutlierCleaner(
                columns=columns,
                method=method,
                strategy=strategy,
                threshold=threshold,
            )
        )
        return self

    def validate(self, rules: list[ValidationRule]) -> "CleanBuilder":
        self.cleaners.append(ValidationCleaner(rules=rules))
        return self

    def apply_recipe(self, recipe: RecipeConfig) -> "CleanBuilder":
        engine = CleanEngine(recipe=recipe)
        self.cleaners.extend(engine.cleaners)
        return self

    def execute(
        self,
    ) -> tuple[list[dict[str, Any]], CleanReport, list[dict[str, Any]]]:
        engine = CleanEngine(cleaners=self.cleaners)
        return engine.run(self.raw_data)

    def save(
        self,
        output_path: str | Path,
        quarantine_path: str | Path | None = None,
        report_path: str | Path | None = None,
    ) -> CleanReport:
        clean_rows, report, quarantined_rows = self.execute()
        self.writer.write(clean_rows, output_path)

        if quarantine_path and quarantined_rows:
            self.writer.write(quarantined_rows, quarantine_path)

        if report_path:
            p = Path(report_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix.lower() == ".json":
                p.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            else:
                p.write_text(report.to_markdown(), encoding="utf-8")

        return report
