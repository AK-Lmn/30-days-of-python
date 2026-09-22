import hashlib
import re
from typing import Any


class RuleEvaluator:
    @staticmethod
    def calculate_bucket(user_id: str, salt: str = "") -> int:
        hash_bytes = hashlib.sha256(f"{user_id}:{salt}".encode("utf-8")).digest()
        hash_int = int.from_bytes(hash_bytes[:4], byteorder="big")
        return hash_int % 100

    @classmethod
    def match_condition(cls, condition_op: str, condition_values: Any, context_val: Any) -> bool:
        if context_val is None:
            return False

        op = condition_op.lower()

        if op == "equals":
            return str(context_val) == str(condition_values)

        if op == "not_equals":
            return str(context_val) != str(condition_values)

        if op == "in":
            if isinstance(condition_values, (list, tuple, set)):
                return str(context_val) in [str(item) for item in condition_values]
            return str(context_val) == str(condition_values)

        if op == "not_in":
            if isinstance(condition_values, (list, tuple, set)):
                return str(context_val) not in [str(item) for item in condition_values]
            return str(context_val) != str(condition_values)

        if op == "contains":
            return str(condition_values) in str(context_val)

        if op == "starts_with":
            return str(context_val).startswith(str(condition_values))

        if op == "ends_with":
            return str(context_val).endswith(str(condition_values))

        if op in ("greater_than", "gt"):
            try:
                return float(context_val) > float(condition_values)
            except (ValueError, TypeError):
                return False

        if op in ("less_than", "lt"):
            try:
                return float(context_val) < float(condition_values)
            except (ValueError, TypeError):
                return False

        if op in ("greater_than_or_equal", "gte"):
            try:
                return float(context_val) >= float(condition_values)
            except (ValueError, TypeError):
                return False

        if op in ("less_than_or_equal", "lte"):
            try:
                return float(context_val) <= float(condition_values)
            except (ValueError, TypeError):
                return False

        if op == "regex":
            try:
                return bool(re.search(str(condition_values), str(context_val)))
            except re.error:
                return False

        return False
