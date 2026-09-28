import math
import statistics
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext
from cleanforge.models.types import OutlierMethod, OutlierStrategy


class OutlierCleaner(BaseCleaner):
    def __init__(
        self,
        columns: list[str],
        method: OutlierMethod = OutlierMethod.IQR,
        strategy: OutlierStrategy = OutlierStrategy.CLIP,
        threshold: float = 1.5,
    ) -> None:
        self.columns = columns
        self.method = method
        self.strategy = strategy
        self.threshold = threshold

    @property
    def name(self) -> str:
        return "OutlierCleaner"

    def _calculate_bounds(
        self, values: list[float]
    ) -> tuple[float, float, float, float]:
        if not values:
            return 0.0, 0.0, 0.0, 0.0

        mean_val = statistics.mean(values)
        median_val = statistics.median(values)

        if self.method == OutlierMethod.ZSCORE:
            stdev = statistics.stdev(values) if len(values) > 1 else 0.0
            lower = mean_val - (self.threshold * stdev)
            upper = mean_val + (self.threshold * stdev)
            return lower, upper, mean_val, median_val

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1_idx = int(n * 0.25)
        q3_idx = int(n * 0.75)
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1
        lower = q1 - (self.threshold * iqr)
        upper = q3 + (self.threshold * iqr)
        return lower, upper, mean_val, median_val

    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        if not rows:
            return rows

        bounds_info: dict[str, tuple[float, float, float, float]] = {}
        for col in self.columns:
            nums: list[float] = []
            for r in rows:
                val = r.get(col)
                if val is not None:
                    try:
                        nums.append(float(val))
                    except (ValueError, TypeError):
                        pass
            if len(nums) >= 4:
                bounds_info[col] = self._calculate_bounds(nums)

        cleaned_rows: list[dict[str, Any]] = []
        for r in rows:
            new_r = dict(r)
            should_drop = False
            drop_reason = ""

            for col in self.columns:
                if col not in bounds_info:
                    continue

                lower, upper, mean_val, median_val = bounds_info[col]
                val = new_r.get(col)
                if val is None:
                    continue

                try:
                    num = float(val)
                except (ValueError, TypeError):
                    continue

                if num < lower or num > upper:
                    context.record_outlier()
                    if self.strategy == OutlierStrategy.DROP:
                        should_drop = True
                        drop_reason = f"Outlier value {num} in column '{col}' outside [{lower:.2f}, {upper:.2f}]"
                        break
                    elif self.strategy == OutlierStrategy.CLIP:
                        clipped = lower if num < lower else upper
                        new_r[col] = type(val)(clipped) if isinstance(val, int) else clipped
                        context.record_modification(col)
                    elif self.strategy == OutlierStrategy.NULLIFY:
                        new_r[col] = None
                        context.record_modification(col)
                    elif self.strategy == OutlierStrategy.MEDIAN:
                        new_r[col] = round(median_val, 2)
                        context.record_modification(col)
                    elif self.strategy == OutlierStrategy.MEAN:
                        new_r[col] = round(mean_val, 2)
                        context.record_modification(col)

            if should_drop:
                context.quarantine(r, drop_reason)
            else:
                cleaned_rows.append(new_r)

        return cleaned_rows
