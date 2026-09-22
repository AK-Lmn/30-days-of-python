from fastapi import APIRouter, Depends, HTTPException, status
from flagforge.core.evaluator import evaluate_flag
from flagforge.dependencies import get_flag_repo, get_metrics_tracker
from flagforge.models.evaluation import (
    EvaluationRequest,
    EvaluationResponse,
    BulkEvaluationRequest,
    BulkEvaluationResponse,
)
from flagforge.repositories.memory import InMemoryFlagRepository, MetricsTracker

router = APIRouter(prefix="/api/v1", tags=["Evaluations"])


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_single_flag(
    request_data: EvaluationRequest,
    flag_repo: InMemoryFlagRepository = Depends(get_flag_repo),
    metrics_tracker: MetricsTracker = Depends(get_metrics_tracker),
):
    flag = await flag_repo.get(request_data.flag_key)
    if not flag:
        if request_data.default_fallback is not None:
            return EvaluationResponse(
                flag_key=request_data.flag_key,
                value=request_data.default_fallback,
                enabled=False,
                reason="FLAG_NOT_FOUND_FALLBACK",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag with key '{request_data.flag_key}' does not exist",
        )

    await metrics_tracker.record_evaluation(flag.key)
    result = evaluate_flag(flag, request_data.context, request_data.default_fallback)
    return result


@router.post("/evaluate-all", response_model=BulkEvaluationResponse)
async def evaluate_bulk_flags(
    request_data: BulkEvaluationRequest,
    flag_repo: InMemoryFlagRepository = Depends(get_flag_repo),
    metrics_tracker: MetricsTracker = Depends(get_metrics_tracker),
):
    flags, _ = await flag_repo.list(limit=1000)
    target_flags = flags

    if request_data.flag_keys is not None:
        target_keys_set = set(request_data.flag_keys)
        target_flags = [f for f in flags if f.key in target_keys_set]

    results: dict[str, EvaluationResponse] = {}
    for flag in target_flags:
        await metrics_tracker.record_evaluation(flag.key)
        results[flag.key] = evaluate_flag(flag, request_data.context)

    return BulkEvaluationResponse(evaluations=results, count=len(results))
