import time
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext
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
from cleanforge.models.recipe import RecipeConfig
from cleanforge.models.report import CleanReport
from cleanforge.profiler.analyzer import DataProfiler


class CleanEngine:
    def __init__(self, recipe: RecipeConfig | None = None, cleaners: list[BaseCleaner] | None = None) -> None:
        self.recipe = recipe
        self.cleaners = cleaners or []
        if self.recipe:
            self._compile_recipe(self.recipe)

    def _compile_recipe(self, recipe: RecipeConfig) -> None:
        if recipe.headers:
            self.cleaners.append(
                HeaderCleaner(
                    casing=recipe.headers.casing,
                    strip_whitespace=recipe.headers.strip_whitespace,
                    remove_special_characters=recipe.headers.remove_special_characters,
                    rename_map=recipe.headers.rename,
                )
            )

        if recipe.missing:
            col_strats = {
                k: (v.strategy, v.fill_value) for k, v in recipe.missing.columns.items()
            }
            self.cleaners.append(
                MissingCleaner(
                    missing_markers=recipe.missing.missing_values,
                    default_strategy=recipe.missing.default_strategy,
                    default_fill_value=recipe.missing.default_fill_value,
                    column_strategies=col_strats,
                    drop_threshold_percent=recipe.missing.drop_threshold_percent,
                )
            )

        if recipe.duplicates and recipe.duplicates.enabled:
            self.cleaners.append(
                DuplicateCleaner(
                    subset=recipe.duplicates.subset,
                    keep=recipe.duplicates.keep,
                    fuzzy=recipe.duplicates.fuzzy,
                    similarity_threshold=recipe.duplicates.similarity_threshold,
                    fuzzy_columns=recipe.duplicates.fuzzy_columns,
                )
            )

        for text_rule in recipe.text:
            self.cleaners.append(
                TextCleaner(
                    columns=text_rule.columns,
                    strip=text_rule.strip,
                    collapse_spaces=text_rule.collapse_spaces,
                    casing=text_rule.casing,
                    remove_html=text_rule.remove_html,
                    normalize_unicode=text_rule.normalize_unicode,
                    regex_replace=text_rule.regex_replace,
                )
            )

        for num_rule in recipe.numbers:
            self.cleaners.append(
                NumberCleaner(
                    columns=num_rule.columns,
                    strip_currency=num_rule.strip_currency,
                    remove_commas=num_rule.remove_commas,
                    parse_percentage=num_rule.parse_percentage,
                    target_type=num_rule.target_type,
                    decimals=num_rule.decimals,
                    fill_on_error=num_rule.fill_on_error,
                )
            )

        for date_rule in recipe.dates:
            self.cleaners.append(
                DateCleaner(
                    columns=date_rule.columns,
                    target_format=date_rule.target_format,
                    input_formats=date_rule.input_formats,
                    fill_on_error=date_rule.fill_on_error,
                )
            )

        for bool_rule in recipe.booleans:
            self.cleaners.append(
                BooleanCleaner(
                    columns=bool_rule.columns,
                    true_values=bool_rule.true_values,
                    false_values=bool_rule.false_values,
                    nullable=bool_rule.nullable,
                )
            )

        for phone_rule in recipe.phones:
            self.cleaners.append(
                PhoneCleaner(
                    columns=phone_rule.columns,
                    phone_format=phone_rule.format,
                    default_country_code=phone_rule.default_country_code,
                )
            )

        for email_rule in recipe.emails:
            self.cleaners.append(
                EmailCleaner(
                    columns=email_rule.columns,
                    lowercase=email_rule.lowercase,
                    action_on_invalid=email_rule.action_on_invalid,
                )
            )

        for outlier_rule in recipe.outliers:
            self.cleaners.append(
                OutlierCleaner(
                    columns=outlier_rule.columns,
                    method=outlier_rule.method,
                    strategy=outlier_rule.strategy,
                    threshold=outlier_rule.threshold,
                )
            )

        if recipe.validations:
            self.cleaners.append(ValidationCleaner(recipe.validations))

    def add_cleaner(self, cleaner: BaseCleaner) -> "CleanEngine":
        self.cleaners.append(cleaner)
        return self

    def run(
        self, rows: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], CleanReport, list[dict[str, Any]]]:
        profiler = DataProfiler()
        initial_profile = profiler.profile(rows)

        start_time = time.perf_counter()
        context = CleanContext()
        current_rows = [dict(r) for r in rows]
        operations_applied: list[str] = []

        for cleaner in self.cleaners:
            operations_applied.append(cleaner.name)
            current_rows = cleaner.clean(current_rows, context)

        final_profile = profiler.profile(current_rows)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        report = CleanReport(
            initial_rows=len(rows),
            final_rows=len(current_rows),
            quarantined_rows=len(context.quarantined_rows),
            initial_health_score=initial_profile.health_score,
            final_health_score=final_profile.health_score,
            operations_applied=operations_applied,
            modifications_by_column=context.modifications,
            dropped_duplicates=context.dropped_duplicates,
            imputed_values=context.imputed_values,
            outliers_handled=context.outliers_handled,
            quarantined_reasons=context.quarantine_reasons,
            execution_time_ms=round(duration_ms, 2),
        )

        return current_rows, report, context.quarantined_rows
