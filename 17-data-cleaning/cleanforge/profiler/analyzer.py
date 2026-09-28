import json
from typing import Any
from cleanforge.models.profile import DatasetProfile, ColumnProfile
from cleanforge.profiler.metrics import compute_column_metrics, calculate_dataset_health_score
from cleanforge.profiler.type_infer import infer_column_type


class DataProfiler:
    def profile(self, rows: list[dict[str, Any]]) -> DatasetProfile:
        if not rows:
            return DatasetProfile(
                row_count=0,
                column_count=0,
                duplicate_rows=0,
                health_score=100.0,
                columns={},
            )

        row_count = len(rows)
        all_columns: list[str] = []
        for r in rows:
            for k in r.keys():
                if k not in all_columns:
                    all_columns.append(k)

        seen_rows: set[str] = set()
        duplicate_rows = 0
        for r in rows:
            serialized = json.dumps(r, sort_keys=True, default=str)
            if serialized in seen_rows:
                duplicate_rows += 1
            else:
                seen_rows.add(serialized)

        columns_data: dict[str, ColumnProfile] = {}
        for col in all_columns:
            values = [r.get(col) for r in rows]
            inferred_type = infer_column_type(values)
            col_profile = compute_column_metrics(col, values, inferred_type)
            columns_data[col] = col_profile

        health_score = calculate_dataset_health_score(
            row_count, duplicate_rows, columns_data
        )

        return DatasetProfile(
            row_count=row_count,
            column_count=len(all_columns),
            duplicate_rows=duplicate_rows,
            health_score=health_score,
            columns=columns_data,
        )
