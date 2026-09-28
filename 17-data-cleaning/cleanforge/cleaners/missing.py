import statistics
from collections import Counter
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext
from cleanforge.models.types import ImputeStrategy


class MissingCleaner(BaseCleaner):
    def __init__(
        self,
        missing_markers: list[str] | None = None,
        default_strategy: ImputeStrategy | None = None,
        default_fill_value: Any | None = None,
        column_strategies: dict[str, tuple[ImputeStrategy, Any | None]] | None = None,
        drop_threshold_percent: float | None = None,
    ) -> None:
        self.missing_markers = set(
            s.strip().lower()
            for s in (
                missing_markers
                if missing_markers is not None
                else ["", "na", "n/a", "null", "none", "nan", "-", "?"]
            )
        )
        self.default_strategy = default_strategy
        self.default_fill_value = default_fill_value
        self.column_strategies = column_strategies or {}
        self.drop_threshold_percent = drop_threshold_percent

    @property
    def name(self) -> str:
        return "MissingCleaner"

    def is_missing(self, val: Any) -> bool:
        if val is None:
            return True
        if isinstance(val, str):
            return val.strip().lower() in self.missing_markers
        return False

    def _calculate_column_stats(
        self, rows: list[dict[str, Any]], column: str
    ) -> tuple[float | None, float | None, Any | None]:
        numeric_values: list[float] = []
        all_valid: list[Any] = []

        for r in rows:
            v = r.get(column)
            if not self.is_missing(v):
                all_valid.append(v)
                try:
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    pass

        mean_val = statistics.mean(numeric_values) if numeric_values else None
        median_val = statistics.median(numeric_values) if numeric_values else None
        mode_val = (
            Counter(all_valid).most_common(1)[0][0] if all_valid else None
        )
        return mean_val, median_val, mode_val

    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        if not rows:
            return rows

        all_columns = list(rows[0].keys())
        total_cols = len(all_columns)

        surviving_rows: list[dict[str, Any]] = []
        for r in rows:
            missing_count = sum(1 for c in all_columns if self.is_missing(r.get(c)))
            if self.drop_threshold_percent is not None and total_cols > 0:
                missing_pct = (missing_count / total_cols) * 100.0
                if missing_pct >= self.drop_threshold_percent:
                    context.quarantine(
                        r, f"Missing {missing_pct:.1f}% fields exceeds threshold"
                    )
                    continue

            should_drop = False
            for col in all_columns:
                if self.is_missing(r.get(col)):
                    strategy_info = self.column_strategies.get(col)
                    strat = strategy_info[0] if strategy_info else self.default_strategy
                    if strat == ImputeStrategy.DROP_ROW:
                        should_drop = True
                        context.quarantine(r, f"Required column '{col}' is missing")
                        break

            if not should_drop:
                surviving_rows.append(r)

        stats_cache: dict[str, tuple[float | None, float | None, Any | None]] = {}
        for col in all_columns:
            stats_cache[col] = self._calculate_column_stats(surviving_rows, col)

        imputed_rows: list[dict[str, Any]] = [dict(r) for r in surviving_rows]

        for col in all_columns:
            strategy_info = self.column_strategies.get(col)
            strat = strategy_info[0] if strategy_info else self.default_strategy
            fill_val = strategy_info[1] if strategy_info else self.default_fill_value

            if strat is None:
                continue

            mean_val, median_val, mode_val = stats_cache[col]

            if strat == ImputeStrategy.FORWARD_FILL:
                last_seen = None
                for row in imputed_rows:
                    val = row.get(col)
                    if self.is_missing(val):
                        if last_seen is not None:
                            row[col] = last_seen
                            context.record_modification(col)
                            context.record_imputation()
                    else:
                        last_seen = val
            elif strat == ImputeStrategy.BACKWARD_FILL:
                next_seen = None
                for i in range(len(imputed_rows) - 1, -1, -1):
                    val = imputed_rows[i].get(col)
                    if self.is_missing(val):
                        if next_seen is not None:
                            imputed_rows[i][col] = next_seen
                            context.record_modification(col)
                            context.record_imputation()
                    else:
                        next_seen = val
            else:
                target_fill = fill_val
                if strat == ImputeStrategy.MEAN and mean_val is not None:
                    target_fill = round(mean_val, 2)
                elif strat == ImputeStrategy.MEDIAN and median_val is not None:
                    target_fill = round(median_val, 2)
                elif strat == ImputeStrategy.MODE and mode_val is not None:
                    target_fill = mode_val

                if target_fill is not None:
                    for row in imputed_rows:
                        if self.is_missing(row.get(col)):
                            row[col] = target_fill
                            context.record_modification(col)
                            context.record_imputation()

        return imputed_rows
