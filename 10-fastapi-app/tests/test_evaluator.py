import pytest
from datetime import datetime, timezone
from flagforge.core.evaluator import compute_rollout_bucket, evaluate_condition, matches_rule, evaluate_flag
from flagforge.models.flag import FlagResponse, FlagType, TargetingRule, RuleCondition, Operator
from flagforge.models.evaluation import EvaluationContext


def test_compute_rollout_bucket_deterministic():
    bucket_a1 = compute_rollout_bucket("feature-alpha", "user-123")
    bucket_a2 = compute_rollout_bucket("feature-alpha", "user-123")
    bucket_b = compute_rollout_bucket("feature-beta", "user-123")
    assert bucket_a1 == bucket_a2
    assert 0 <= bucket_a1 < 100
    assert 0 <= bucket_b < 100


def test_evaluate_condition_equals():
    cond = RuleCondition(attribute="role", operator=Operator.EQUALS, value="admin")
    assert evaluate_condition(cond, {"role": "admin"}) is True
    assert evaluate_condition(cond, {"role": "user"}) is False
    assert evaluate_condition(cond, {}) is False


def test_evaluate_condition_not_equals():
    cond = RuleCondition(attribute="status", operator=Operator.NOT_EQUALS, value="banned")
    assert evaluate_condition(cond, {"status": "active"}) is True
    assert evaluate_condition(cond, {"status": "banned"}) is False


def test_evaluate_condition_contains():
    cond = RuleCondition(attribute="email", operator=Operator.CONTAINS, value="corp")
    assert evaluate_condition(cond, {"email": "alice@corp.com"}) is True
    assert evaluate_condition(cond, {"email": "bob@gmail.com"}) is False


def test_evaluate_condition_in_and_not_in():
    cond_in = RuleCondition(attribute="country", operator=Operator.IN, value=["US", "CA", "GB"])
    assert evaluate_condition(cond_in, {"country": "CA"}) is True
    assert evaluate_condition(cond_in, {"country": "FR"}) is False

    cond_not_in = RuleCondition(attribute="country", operator=Operator.NOT_IN, value=["RU", "NK"])
    assert evaluate_condition(cond_not_in, {"country": "DE"}) is True
    assert evaluate_condition(cond_not_in, {"country": "RU"}) is False


def test_evaluate_condition_numeric_comparisons():
    cond_gt = RuleCondition(attribute="score", operator=Operator.GREATER_THAN, value=50)
    assert evaluate_condition(cond_gt, {"score": 75}) is True
    assert evaluate_condition(cond_gt, {"score": 50}) is False
    assert evaluate_condition(cond_gt, {"score": "invalid"}) is False

    cond_lt = RuleCondition(attribute="latency", operator=Operator.LESS_THAN, value=200)
    assert evaluate_condition(cond_lt, {"latency": 150}) is True
    assert evaluate_condition(cond_lt, {"latency": 250}) is False


def test_evaluate_condition_string_boundary():
    cond_sw = RuleCondition(attribute="path", operator=Operator.STARTS_WITH, value="/api/v1")
    assert evaluate_condition(cond_sw, {"path": "/api/v1/users"}) is True
    assert evaluate_condition(cond_sw, {"path": "/health"}) is False

    cond_ew = RuleCondition(attribute="email", operator=Operator.ENDS_WITH, value="@company.internal")
    assert evaluate_condition(cond_ew, {"email": "dev@company.internal"}) is True
    assert evaluate_condition(cond_ew, {"email": "dev@gmail.com"}) is False


def test_evaluate_flag_disabled_returns_default():
    flag = FlagResponse(
        key="disabled-flag",
        name="Disabled Flag",
        description="",
        flag_type=FlagType.BOOLEAN,
        enabled=False,
        default_value=False,
        rules=[],
        tags=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        version=1,
    )
    context = EvaluationContext(entity_id="user-1")
    res = evaluate_flag(flag, context)
    assert res.enabled is False
    assert res.value is False
    assert res.reason == "FLAG_DISABLED"


def test_evaluate_flag_rules_match():
    rule = TargetingRule(
        id="rule-premium",
        name="Premium Plan",
        conditions=[
            RuleCondition(attribute="plan", operator=Operator.EQUALS, value="premium")
        ],
        serve_value="unlimited_storage",
    )
    flag = FlagResponse(
        key="storage-tier",
        name="Storage Tier",
        description="",
        flag_type=FlagType.STRING,
        enabled=True,
        default_value="standard_storage",
        rules=[rule],
        tags=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        version=1,
    )

    matching_context = EvaluationContext(entity_id="user-1", attributes={"plan": "premium"})
    res_match = evaluate_flag(flag, matching_context)
    assert res_match.value == "unlimited_storage"
    assert res_match.rule_id == "rule-premium"
    assert res_match.reason == "RULE_MATCH"

    non_matching_context = EvaluationContext(entity_id="user-2", attributes={"plan": "free"})
    res_default = evaluate_flag(flag, non_matching_context)
    assert res_default.value == "standard_storage"
    assert res_default.rule_id is None
    assert res_default.reason == "DEFAULT_VALUE"


def test_evaluate_flag_percentage_rollout():
    flag_key = "rollout-test"
    rule = TargetingRule(
        id="rollout-50",
        name="50 Percent Rollout",
        conditions=[],
        serve_value="variant_b",
        rollout_percentage=50,
    )
    flag = FlagResponse(
        key=flag_key,
        name="Rollout Test",
        description="",
        flag_type=FlagType.STRING,
        enabled=True,
        default_value="variant_a",
        rules=[rule],
        tags=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        version=1,
    )

    matched_count = 0
    total = 200
    for idx in range(total):
        context = EvaluationContext(entity_id=f"simulated-user-{idx}")
        res = evaluate_flag(flag, context)
        if res.value == "variant_b":
            matched_count += 1

    assert 70 <= matched_count <= 130
