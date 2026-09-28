from typing import Any
from pydantic import BaseModel, Field


class CleanReport(BaseModel):
    initial_rows: int = 0
    final_rows: int = 0
    quarantined_rows: int = 0
    initial_health_score: float = 0.0
    final_health_score: float = 0.0
    operations_applied: list[str] = Field(default_factory=list)
    modifications_by_column: dict[str, int] = Field(default_factory=dict)
    dropped_duplicates: int = 0
    imputed_values: int = 0
    outliers_handled: int = 0
    quarantined_reasons: dict[str, int] = Field(default_factory=dict)
    execution_time_ms: float = 0.0

    def to_markdown(self) -> str:
        lines = [
            "# CleanForge Remediation Audit Report",
            "",
            "## Summary",
            f"- **Initial Rows:** {self.initial_rows}",
            f"- **Final Clean Rows:** {self.final_rows}",
            f"- **Quarantined Rows:** {self.quarantined_rows}",
            f"- **Dropped Duplicates:** {self.dropped_duplicates}",
            f"- **Imputed Missing Values:** {self.imputed_values}",
            f"- **Outliers Remediated:** {self.outliers_handled}",
            f"- **Initial Health Score:** {self.initial_health_score:.1f}%",
            f"- **Final Health Score:** {self.final_health_score:.1f}%",
            f"- **Score Improvement:** +{max(0.0, self.final_health_score - self.initial_health_score):.1f}%",
            f"- **Execution Time:** {self.execution_time_ms:.2f} ms",
            "",
            "## Executed Operations",
        ]
        if self.operations_applied:
            for op in self.operations_applied:
                lines.append(f"- {op}")
        else:
            lines.append("- None")

        lines.append("")
        lines.append("## Column Modifications")
        if self.modifications_by_column:
            lines.append("| Column | Values Modified |")
            lines.append("| :--- | :--- |")
            for col, count in sorted(self.modifications_by_column.items()):
                lines.append(f"| {col} | {count} |")
        else:
            lines.append("No column modifications recorded.")

        if self.quarantined_reasons:
            lines.append("")
            lines.append("## Quarantine Reasons")
            lines.append("| Reason | Violated Rows |")
            lines.append("| :--- | :--- |")
            for reason, count in sorted(self.quarantined_reasons.items()):
                lines.append(f"| {reason} | {count} |")

        return "\n".join(lines)
