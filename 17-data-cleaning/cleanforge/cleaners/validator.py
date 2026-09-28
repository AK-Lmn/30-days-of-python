import re
from typing import Any
from cleanforge.cleaners.base import BaseCleaner, CleanContext
from cleanforge.models.recipe import ValidationRule


class ValidationCleaner(BaseCleaner):
    def __init__(self, rules: list[ValidationRule]) -> None:
        self.rules = rules

    @property
    def name(self) -> str:
        return "ValidationCleaner"

    def clean(
        self, rows: list[dict[str, Any]], context: CleanContext
    ) -> list[dict[str, Any]]:
        cleaned_rows: list[dict[str, Any]] = []

        for r in rows:
            new_r = dict(r)
            quarantine_row = False
            quarantine_reason = ""
            drop_row = False

            for rule in self.rules:
                col = rule.column
                if col not in new_r:
                    continue

                val = new_r.get(col)

                if rule.not_null and (val is None or str(val).strip() == ""):
                    if rule.action == "quarantine":
                        quarantine_row = True
                        quarantine_reason = f"Constraint failed: '{col}' cannot be null"
                        break
                    elif rule.action == "drop":
                        drop_row = True
                        break

                if val is not None and str(val).strip() != "":
                    if rule.min_value is not None or rule.max_value is not None:
                        try:
                            num = float(val)
                            if rule.min_value is not None and num < rule.min_value:
                                if rule.action == "quarantine":
                                    quarantine_row = True
                                    quarantine_reason = f"Constraint failed: '{col}' value {num} < min {rule.min_value}"
                                    break
                                elif rule.action == "drop":
                                    drop_row = True
                                    break
                                elif rule.action == "nullify":
                                    new_r[col] = None
                                    context.record_modification(col)

                            if rule.max_value is not None and num > rule.max_value:
                                if rule.action == "quarantine":
                                    quarantine_row = True
                                    quarantine_reason = f"Constraint failed: '{col}' value {num} > max {rule.max_value}"
                                    break
                                elif rule.action == "drop":
                                    drop_row = True
                                    break
                                elif rule.action == "nullify":
                                    new_r[col] = None
                                    context.record_modification(col)
                        except (ValueError, TypeError):
                            pass

                    if rule.allowed_values is not None:
                        allowed_set = {str(x).strip().lower() for x in rule.allowed_values}
                        if str(val).strip().lower() not in allowed_set:
                            if rule.action == "quarantine":
                                quarantine_row = True
                                quarantine_reason = f"Constraint failed: '{col}' value '{val}' not in allowed values"
                                break
                            elif rule.action == "drop":
                                drop_row = True
                                break
                            elif rule.action == "nullify":
                                new_r[col] = None
                                context.record_modification(col)

                    if rule.regex_pattern is not None:
                        if not re.search(rule.regex_pattern, str(val)):
                            if rule.action == "quarantine":
                                quarantine_row = True
                                quarantine_reason = f"Constraint failed: '{col}' value '{val}' does not match regex '{rule.regex_pattern}'"
                                break
                            elif rule.action == "drop":
                                drop_row = True
                                break
                            elif rule.action == "nullify":
                                new_r[col] = None
                                context.record_modification(col)

            if quarantine_row:
                context.quarantine(r, quarantine_reason)
            elif not drop_row:
                cleaned_rows.append(new_r)

        return cleaned_rows
