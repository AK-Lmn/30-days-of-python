import re
from typing import Any

from autoflow.engine.templating import extract_context_value
from autoflow.models.enums import ComparisonOperator


def evaluate_single_condition(condition: dict[str, Any], context: dict[str, Any]) -> bool:
    field = condition.get("field", "")
    operator = condition.get("operator", ComparisonOperator.EQUALS.value)
    expected_value = condition.get("value")

    actual_value = extract_context_value(field, context)

    if operator == ComparisonOperator.IS_NULL.value or operator == ComparisonOperator.IS_NULL:
        return actual_value is None or actual_value == ""

    if operator == ComparisonOperator.IS_NOT_NULL.value or operator == ComparisonOperator.IS_NOT_NULL:
        return actual_value is not None and actual_value != ""

    if actual_value is None:
        return False

    if operator in (ComparisonOperator.EQUALS.value, ComparisonOperator.EQUALS):
        return str(actual_value) == str(expected_value) if isinstance(expected_value, str) else actual_value == expected_value

    if operator in (ComparisonOperator.NOT_EQUALS.value, ComparisonOperator.NOT_EQUALS):
        return str(actual_value) != str(expected_value) if isinstance(expected_value, str) else actual_value != expected_value

    if operator in (ComparisonOperator.GREATER_THAN.value, ComparisonOperator.GREATER_THAN):
        try:
            return float(actual_value) > float(expected_value)
        except (ValueError, TypeError):
            return False

    if operator in (ComparisonOperator.GREATER_THAN_OR_EQUAL.value, ComparisonOperator.GREATER_THAN_OR_EQUAL):
        try:
            return float(actual_value) >= float(expected_value)
        except (ValueError, TypeError):
            return False

    if operator in (ComparisonOperator.LESS_THAN.value, ComparisonOperator.LESS_THAN):
        try:
            return float(actual_value) < float(expected_value)
        except (ValueError, TypeError):
            return False

    if operator in (ComparisonOperator.LESS_THAN_OR_EQUAL.value, ComparisonOperator.LESS_THAN_OR_EQUAL):
        try:
            return float(actual_value) <= float(expected_value)
        except (ValueError, TypeError):
            return False

    if operator in (ComparisonOperator.CONTAINS.value, ComparisonOperator.CONTAINS):
        if isinstance(actual_value, (list, tuple, set)):
            return expected_value in actual_value
        return str(expected_value) in str(actual_value)

    if operator in (ComparisonOperator.NOT_CONTAINS.value, ComparisonOperator.NOT_CONTAINS):
        if isinstance(actual_value, (list, tuple, set)):
            return expected_value not in actual_value
        return str(expected_value) not in str(actual_value)

    if operator in (ComparisonOperator.STARTS_WITH.value, ComparisonOperator.STARTS_WITH):
        return str(actual_value).startswith(str(expected_value))

    if operator in (ComparisonOperator.ENDS_WITH.value, ComparisonOperator.ENDS_WITH):
        return str(actual_value).endswith(str(expected_value))

    if operator in (ComparisonOperator.MATCHES_REGEX.value, ComparisonOperator.MATCHES_REGEX):
        try:
            return bool(re.search(str(expected_value), str(actual_value)))
        except re.error:
            return False

    return False


def evaluate_conditions(conditions: list[dict[str, Any]], context: dict[str, Any]) -> bool:
    if not conditions:
        return True
    return all(evaluate_single_condition(cond, context) for cond in conditions)
