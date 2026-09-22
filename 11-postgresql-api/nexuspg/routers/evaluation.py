from fastapi import APIRouter, Depends
from nexuspg.core.errors import EntityNotFoundError
from nexuspg.core.evaluator import RuleEvaluator
from nexuspg.dependencies import get_flag_repo, get_project_repo
from nexuspg.repositories.flag_repo import FlagRepository
from nexuspg.repositories.project_repo import ProjectRepository
from nexuspg.schemas.evaluation import (
    BulkEvaluationRequest,
    BulkEvaluationResponse,
    EvaluationRequest,
    FlagEvaluationResult,
)

router = APIRouter(
    prefix="/projects/{project_key}/environments/{env_key}/evaluate",
    tags=["Evaluation"],
)


def evaluate_single_flag(
    flag_key: str,
    flag_type: str,
    default_val: any,
    state_enabled: bool,
    state_pct: int,
    state_variant_val: any,
    rules: list,
    user_id: str | None,
    attributes: dict,
) -> FlagEvaluationResult:
    if not state_enabled:
        return FlagEvaluationResult(
            flag_key=flag_key,
            enabled=False,
            value=default_val,
            reason="FLAG_DISABLED",
        )

    for rule in rules:
        all_conditions_matched = True
        for cond in rule.conditions:
            ctx_val = attributes.get(cond.attribute)
            if not RuleEvaluator.match_condition(cond.operator, cond.values, ctx_val):
                all_conditions_matched = False
                break

        if all_conditions_matched and rule.conditions:
            if rule.percentage < 100 and user_id:
                bucket = RuleEvaluator.calculate_bucket(user_id, salt=f"rule:{rule.id}")
                if bucket >= rule.percentage:
                    continue

            return FlagEvaluationResult(
                flag_key=flag_key,
                enabled=True,
                value=rule.serve_value,
                reason=f"RULE_MATCH: {rule.name}",
                rule_id=str(rule.id),
            )

    if state_pct < 100 and user_id:
        bucket = RuleEvaluator.calculate_bucket(user_id, salt=f"flag:{flag_key}")
        if bucket >= state_pct:
            return FlagEvaluationResult(
                flag_key=flag_key,
                enabled=False,
                value=default_val,
                reason="PERCENTAGE_ROLLOUT_EXCLUDED",
            )

    serve_val = state_variant_val if state_variant_val is not None else default_val
    if flag_type == "boolean" and serve_val is False and state_enabled:
        serve_val = True

    return FlagEvaluationResult(
        flag_key=flag_key,
        enabled=True,
        value=serve_val,
        reason="DEFAULT_TARGETING",
    )


@router.post("", response_model=BulkEvaluationResponse)
async def evaluate_all_flags(
    project_key: str,
    env_key: str,
    request: BulkEvaluationRequest,
    project_repo: ProjectRepository = Depends(get_project_repo),
    flag_repo: FlagRepository = Depends(get_flag_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    env = await project_repo.get_environment_by_key(project.id, env_key)
    if not env:
        raise EntityNotFoundError("Environment", env_key)

    pairs = await flag_repo.list_for_evaluation(project.id, env.id, request.flag_keys)

    results: dict[str, FlagEvaluationResult] = {}
    for flag, state in pairs:
        res = evaluate_single_flag(
            flag_key=flag.key,
            flag_type=flag.flag_type,
            default_val=flag.default_value,
            state_enabled=state.enabled,
            state_pct=state.percentage,
            state_variant_val=state.variant_value,
            rules=state.rules,
            user_id=request.context.user_id,
            attributes=request.context.attributes,
        )
        results[flag.key] = res

    return BulkEvaluationResponse(results=results)


@router.post("/{flag_key}", response_model=FlagEvaluationResult)
async def evaluate_flag(
    project_key: str,
    env_key: str,
    flag_key: str,
    request: EvaluationRequest,
    project_repo: ProjectRepository = Depends(get_project_repo),
    flag_repo: FlagRepository = Depends(get_flag_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    env = await project_repo.get_environment_by_key(project.id, env_key)
    if not env:
        raise EntityNotFoundError("Environment", env_key)

    pairs = await flag_repo.list_for_evaluation(project.id, env.id, [flag_key])
    if not pairs:
        raise EntityNotFoundError("Flag", flag_key)

    flag, state = pairs[0]
    return evaluate_single_flag(
        flag_key=flag.key,
        flag_type=flag.flag_type,
        default_val=flag.default_value,
        state_enabled=state.enabled,
        state_pct=state.percentage,
        state_variant_val=state.variant_value,
        rules=state.rules,
        user_id=request.context.user_id,
        attributes=request.context.attributes,
    )
