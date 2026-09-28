from collections import defaultdict
from typing import Any
from pipeforge.models.record import Record


class BatchAggregator:
    def __init__(
        self,
        group_by: list[str],
        aggregations: dict[str, tuple[str, str]],
    ):
        self.group_by = group_by
        self.aggregations = aggregations

    def aggregate(self, records: list[Record]) -> list[Record]:
        groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for r in records:
            key = tuple(r.data.get(k) for k in self.group_by)
            groups[key].append(r.data)

        aggregated_records: list[Record] = []
        row_num = 0
        for group_key, row_list in groups.items():
            row_num += 1
            result_data: dict[str, Any] = {}
            for idx, key_col in enumerate(self.group_by):
                result_data[key_col] = group_key[idx]

            for target_field, (source_col, agg_func) in self.aggregations.items():
                func_name = agg_func.lower()
                vals = [r[source_col] for r in row_list if source_col in r and r[source_col] is not None]
                if func_name == "count":
                    result_data[target_field] = len(row_list)
                elif func_name == "sum":
                    result_data[target_field] = sum(float(v) for v in vals) if vals else 0
                elif func_name == "avg" or func_name == "mean":
                    result_data[target_field] = round(sum(float(v) for v in vals) / len(vals), 4) if vals else 0.0
                elif func_name == "min":
                    result_data[target_field] = min(vals) if vals else None
                elif func_name == "max":
                    result_data[target_field] = max(vals) if vals else None
                elif func_name == "first":
                    result_data[target_field] = vals[0] if vals else None
                elif func_name == "last":
                    result_data[target_field] = vals[-1] if vals else None

            aggregated_records.append(
                Record.from_raw(
                    raw=result_data,
                    row_number=row_num,
                    metadata={"aggregated": True},
                )
            )

        return aggregated_records
