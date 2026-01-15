from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.database import get_db
from app.models import ConversationRun, ConversationTurn, RunStatus
from app.schemas.conversation import (
    ConversationRunCreate,
    ConversationRunDetailResponse,
    ConversationRunListResponse,
    ConversationMetricsListResponse,
    ConversationMetricsResponse,
    ConversationCompareResponse,
    ConversationStartResponse,
)
from app.schemas.common import StatusEnum
from app.services.conversations import run_conversation

router = APIRouter()

ALLOWED_MODEL_IDS = {
    "claude-opus-4-5-20251101",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
}

VERBATIM_CONDITIONS = {"baseline", "naive", "budgeted", "verbatim"}


def _is_verbatim_request(request: ConversationRunCreate) -> bool:
    if request.condition in VERBATIM_CONDITIONS:
        return True
    if request.parameters and request.parameters.get("project") == "verbatim":
        return True
    return bool(request.parameters and request.parameters.get("verbatim") is True)


@router.post("/run", response_model=ConversationStartResponse)
async def start_conversation_run(
    request: ConversationRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if not request.turns:
        raise HTTPException(status_code=400, detail="Conversation turns are required")

    if _is_verbatim_request(request):
        if request.condition not in VERBATIM_CONDITIONS:
            raise HTTPException(
                status_code=400,
                detail="Conversation condition must be one of: baseline, naive, budgeted, verbatim",
            )

        if len(request.turns) != 12:
            raise HTTPException(
                status_code=400,
                detail="Conversation must contain exactly 12 turns",
            )

        if request.model.model_id not in ALLOWED_MODEL_IDS:
            raise HTTPException(
                status_code=400,
                detail=f"Model id '{request.model.model_id}' is not allowed",
            )

    parameters = request.parameters or {}
    if "model" not in parameters:
        parameters["model"] = request.model.model_id
    if "temperature" not in parameters:
        parameters["temperature"] = request.model.temperature
    if "max_tokens" not in parameters:
        parameters["max_tokens"] = request.model.max_tokens

    run = ConversationRun(
        condition=request.condition,
        model=request.model.model_id,
        status=RunStatus.PENDING,
        intent_id=request.intent_id,
        system_prompt=request.system_prompt,
        parameters=parameters,
        turn_count=len(request.turns),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    background_tasks.add_task(
        run_conversation_background,
        run.id,
        request.turns,
        request.model,
        request.system_prompt,
        parameters,
    )

    return ConversationStartResponse(
        run_id=run.id,
        status=StatusEnum.PENDING,
        message=f"Conversation run queued for {len(request.turns)} turns",
    )


async def run_conversation_background(
    run_id: UUID,
    turns: list[str],
    model_config: dict | object,
    system_prompt: str | None,
    parameters: dict | None,
):
    from app.database import AsyncSessionLocal
    from app.schemas.evaluation import ModelConfig

    async with AsyncSessionLocal() as db:
        config = model_config if isinstance(model_config, ModelConfig) else ModelConfig(**model_config)
        await run_conversation(db, run_id, turns, config, system_prompt, parameters)


@router.get("/runs", response_model=ConversationRunListResponse)
async def list_conversation_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    condition: str | None = None,
    status: StatusEnum | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ConversationRun)
    if condition:
        query = query.where(ConversationRun.condition == condition)
    if status:
        query = query.where(ConversationRun.status == status)

    query = query.offset(skip).limit(limit).order_by(ConversationRun.timestamp.desc())

    result = await db.execute(query)
    runs = result.scalars().all()

    from sqlalchemy import func
    count_query = select(func.count(ConversationRun.id))
    if condition:
        count_query = count_query.where(ConversationRun.condition == condition)
    if status:
        count_query = count_query.where(ConversationRun.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return ConversationRunListResponse(runs=runs, total=total)


# NOTE: /metrics and /compare must be defined BEFORE /{run_id} to avoid route conflicts
@router.get("/metrics", response_model=ConversationMetricsListResponse)
async def list_conversation_metrics(
    condition: str | None = None,
    model: str | None = None,
    intent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ConversationRun).options(selectinload(ConversationRun.evaluator_results))
    if condition:
        query = query.where(ConversationRun.condition == condition)
    if model:
        query = query.where(ConversationRun.model == model)
    if intent_id:
        query = query.where(ConversationRun.intent_id == intent_id)

    result = await db.execute(query)
    runs = result.scalars().all()

    metrics: list[ConversationMetricsResponse] = []
    for run in runs:
        eval_result = next(
            (res for res in run.evaluator_results if res.evaluator_name == "verbosity_stability"),
            None,
        )
        metrics.append(
            ConversationMetricsResponse(
                run_id=run.id,
                condition=run.condition,
                model=run.model,
                intent_id=run.intent_id,
                metrics=(eval_result.details if eval_result else {}),
                passed=eval_result.passed if eval_result else None,
            )
        )

    return ConversationMetricsListResponse(runs=metrics)


@router.get("/compare", response_model=ConversationCompareResponse)
async def compare_conversation_conditions(
    condition_a: str = Query(...),
    condition_b: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConversationRun).options(selectinload(ConversationRun.evaluator_results))
        .where(ConversationRun.condition.in_([condition_a, condition_b]))
    )
    runs = result.scalars().all()

    def collect(condition: str) -> list[dict]:
        collected = []
        for run in runs:
            if run.condition != condition:
                continue
            eval_result = next(
                (res for res in run.evaluator_results if res.evaluator_name == "verbosity_stability"),
                None,
            )
            if eval_result and isinstance(eval_result.details, dict):
                collected.append(eval_result.details)
        return collected

    def average_metric(values: list[dict], key: str) -> float | None:
        numeric = [v.get(key) for v in values if isinstance(v.get(key), (int, float))]
        if not numeric:
            return None
        return round(sum(numeric) / len(numeric), 3)

    def summarize(values: list[dict]) -> dict[str, float | None]:
        metrics_only = [v.get("metrics", {}) for v in values]
        fallback_rates = [v.get("fallback_rate") for v in values]
        return {
            "mean_tokens_per_turn": average_metric(metrics_only, "mean_tokens_per_turn"),
            "drift_slope": average_metric(metrics_only, "drift_slope"),
            "length_stddev": average_metric(metrics_only, "length_stddev"),
            "growth_ratio": average_metric(metrics_only, "growth_ratio"),
            "fallback_rate": average_metric([{"fallback_rate": fr} for fr in fallback_rates], "fallback_rate"),
            "runs": len(values),
        }

    values_a = collect(condition_a)
    values_b = collect(condition_b)

    metrics_a = summarize(values_a)
    metrics_b = summarize(values_b)
    deltas = {}
    for key in ("mean_tokens_per_turn", "drift_slope", "length_stddev", "growth_ratio", "fallback_rate"):
        if metrics_a.get(key) is None or metrics_b.get(key) is None:
            deltas[key] = None
        else:
            deltas[key] = round(metrics_b[key] - metrics_a[key], 3)

    return ConversationCompareResponse(
        condition_a=condition_a,
        condition_b=condition_b,
        metrics={
            "condition_a": metrics_a,
            "condition_b": metrics_b,
            "delta": deltas,
        },
    )


# Dynamic route must come AFTER static routes like /metrics and /compare
@router.get("/{run_id}", response_model=ConversationRunDetailResponse)
async def get_conversation_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConversationRun)
        .options(
            selectinload(ConversationRun.turns)
            .selectinload(ConversationTurn.evaluator_results),
            selectinload(ConversationRun.evaluator_results),
        )
        .where(ConversationRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Conversation run not found")

    return ConversationRunDetailResponse.model_validate(run)
