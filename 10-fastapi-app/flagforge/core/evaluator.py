import hashlib
from typing import Any, Optional
from flagforge.models.flag import FlagResponse, Operator, RuleCondition, TargetingRule
from flagforge.models.evaluation import EvaluationContext, EvaluationResponse


def compute_rollout_bucket(flag_key: str, entity_id: str) -> int:
    hash_bytes = hashlib.sha256(f"{flag_key}:{entity_id}".encode("utf-8")).digest()
    integer_value = int.from_bytes(hash_bytes[:4], byteorder="big")
    return integer_value % 100


def evaluate_condition(condition: RuleCondition, attributes: dict[str, Any]) -> bool:
    if condition.attribute not in attributes:
        return False

    current_val = attributes[condition.attribute]
    target_val = condition.value

    try:
        match condition.operator:
            case Operator.EQUALS:
                return current_val == target_val
            case Operator.NOT_EQUALS:
                return current_val != target_val
            case Operator.CONTAINS:
                return str(target_val) in str(current_val)
            case Operator.IN:
                return isinstance(target_val, (list, tuple, set)) and current_val in target_val
            case Operator.NOT_IN:
                return isinstance(target_val, (list, tuple, set)) and current_val not in target_val
            case Operator.GREATER_THAN:
                return float(current_val) > float(target_val)
            case Operator.LESS_THAN:
                return float(current_val) < float(target_val)
            case Operator.STARTS_WITH:
                return str(current_val).startswith(str(target_val))
            case Operator.ENDS_WITH:
                return str(current_val).endswith(str(target_val))
            case _:
                return False
    except (ValueError, TypeError):
        return False


def matches_rule(rule: TargetingRule, context: EvaluationContext) -> bool:
    if not rule.conditions:
        return True
    return all(evaluate_condition(cond, context.attributes) for cond in rule.conditions)


def evaluate_flag(
    flag: FlagResponse,
    context: EvaluationContext,
    fallback: Optional[Any] = None,
) -> EvaluationResponse:
    if not flag.enabled:
        return EvaluationResponse(
            flag_key=flag.key,
            value=flag.default_value if fallback is None else fallback,
            enabled=False,
            reason="FLAG_DISABLED",
        )

    for rule in flag.rules:
        if matches_rule(rule, context):
            if rule.rollout_percentage is not None:
                bucket = compute_rollout_bucket(flag.key, context.entity_id)
                if bucket < rule.rollout_percentage:
                    return EvaluationResponse(
                        flag_key=flag.key,
                        value=rule.serve_value,
                        enabled=True,
                        rule_id=rule.id,
                        reason="RULE_ROLLOUT_MATCH",
                    )
            else:
                return EvaluationResponse(
                    flag_key=flag.key,
                    value=rule.serve_value,
                    enabled=True,
                    rule_id=rule.id,
                    reason="RULE_MATCH",
                )

    return EvaluationResponse(
        flag_key=flag.key,
        value=flag.default_value,
        enabled=True,
        reason="DEFAULT_VALUE",
    )
