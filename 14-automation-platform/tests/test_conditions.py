from autoflow.engine.conditions import evaluate_conditions, evaluate_single_condition
from autoflow.models.enums import ComparisonOperator


def test_condition_equals():
    ctx = {"event": {"status": "active", "code": 200}}
    assert evaluate_single_condition({"field": "event.status", "operator": ComparisonOperator.EQUALS, "value": "active"}, ctx)
    assert not evaluate_single_condition({"field": "event.status", "operator": ComparisonOperator.EQUALS, "value": "inactive"}, ctx)
    assert evaluate_single_condition({"field": "event.code", "operator": ComparisonOperator.EQUALS, "value": 200}, ctx)


def test_condition_not_equals():
    ctx = {"event": {"status": "active"}}
    assert evaluate_single_condition({"field": "event.status", "operator": ComparisonOperator.NOT_EQUALS, "value": "closed"}, ctx)
    assert not evaluate_single_condition({"field": "event.status", "operator": ComparisonOperator.NOT_EQUALS, "value": "active"}, ctx)


def test_condition_numerical_comparisons():
    ctx = {"event": {"price": 100.5}}
    assert evaluate_single_condition({"field": "event.price", "operator": ComparisonOperator.GREATER_THAN, "value": 100}, ctx)
    assert evaluate_single_condition({"field": "event.price", "operator": ComparisonOperator.GREATER_THAN_OR_EQUAL, "value": 100.5}, ctx)
    assert evaluate_single_condition({"field": "event.price", "operator": ComparisonOperator.LESS_THAN, "value": 200}, ctx)
    assert evaluate_single_condition({"field": "event.price", "operator": ComparisonOperator.LESS_THAN_OR_EQUAL, "value": 100.5}, ctx)
    assert not evaluate_single_condition({"field": "event.price", "operator": ComparisonOperator.GREATER_THAN, "value": 200}, ctx)


def test_condition_contains_and_starts_ends():
    ctx = {"event": {"email": "alice@example.com", "roles": ["admin", "editor"]}}
    assert evaluate_single_condition({"field": "event.email", "operator": ComparisonOperator.CONTAINS, "value": "@example.com"}, ctx)
    assert evaluate_single_condition({"field": "event.roles", "operator": ComparisonOperator.CONTAINS, "value": "admin"}, ctx)
    assert evaluate_single_condition({"field": "event.roles", "operator": ComparisonOperator.NOT_CONTAINS, "value": "guest"}, ctx)
    assert evaluate_single_condition({"field": "event.email", "operator": ComparisonOperator.STARTS_WITH, "value": "alice"}, ctx)
    assert evaluate_single_condition({"field": "event.email", "operator": ComparisonOperator.ENDS_WITH, "value": ".com"}, ctx)


def test_condition_null_and_regex():
    ctx = {"event": {"missing": None, "present": "hello", "code": "TX-9988"}}
    assert evaluate_single_condition({"field": "event.missing", "operator": ComparisonOperator.IS_NULL}, ctx)
    assert not evaluate_single_condition({"field": "event.present", "operator": ComparisonOperator.IS_NULL}, ctx)
    assert evaluate_single_condition({"field": "event.present", "operator": ComparisonOperator.IS_NOT_NULL}, ctx)
    assert evaluate_single_condition({"field": "event.code", "operator": ComparisonOperator.MATCHES_REGEX, "value": r"^TX-\d+$"}, ctx)


def test_evaluate_conditions_multi():
    ctx = {"event": {"amount": 250, "country": "US"}}
    conditions = [
        {"field": "event.amount", "operator": ComparisonOperator.GREATER_THAN, "value": 100},
        {"field": "event.country", "operator": ComparisonOperator.EQUALS, "value": "US"},
    ]
    assert evaluate_conditions(conditions, ctx)

    failing_conditions = [
        {"field": "event.amount", "operator": ComparisonOperator.GREATER_THAN, "value": 500},
        {"field": "event.country", "operator": ComparisonOperator.EQUALS, "value": "US"},
    ]
    assert not evaluate_conditions(failing_conditions, ctx)
