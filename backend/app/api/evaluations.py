import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.database import get_db
from app.models import EvaluationRun, EvaluationOutput, TestCase, RunStatus
from app.schemas.evaluation import (
    EvaluationRunCreate,
    EvaluationRunResponse,
    EvaluationRunDetailResponse,
    EvaluationRunListResponse,
    EvaluationStartResponse,
)
from app.schemas.common import StatusEnum
from app.services.evaluation import run_evaluation
from app.services.evaluator_runner import run_evaluators_on_run
from app.evaluators import EVALUATOR_REGISTRY

router = APIRouter()


@router.post("/run", response_model=EvaluationStartResponse)
async def start_evaluation(
    request: EvaluationRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new evaluation run.

    This queues the evaluation to run in the background and returns immediately
    with a run_id that can be used to check progress.
    """
    # Validate test cases exist
    result = await db.execute(
        select(TestCase.id).where(TestCase.id.in_(request.test_case_ids))
    )
    existing_ids = set(row[0] for row in result.all())
    missing_ids = set(request.test_case_ids) - existing_ids

    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Test cases not found: {[str(id) for id in missing_ids]}"
        )

    # Validate evaluator names if provided
    if request.evaluators:
        invalid = [e for e in request.evaluators if e not in EVALUATOR_REGISTRY]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown evaluators: {invalid}. Available: {list(EVALUATOR_REGISTRY.keys())}"
            )

    # Create the evaluation run
    run = EvaluationRun(
        prompt_version=request.prompt_version,
        models=[m.model_dump() for m in request.models],
        status=RunStatus.PENDING,
        test_case_count=len(request.test_case_ids) * len(request.models),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Queue the evaluation to run in background
    # Note: In production, you'd use a proper task queue (Celery, etc.)
    background_tasks.add_task(
        run_evaluation_background,
        run.id,
        request.test_case_ids,
        request.models,
        request.evaluators,
    )

    return EvaluationStartResponse(
        run_id=run.id,
        status=StatusEnum.PENDING,
        message=f"Evaluation started with {len(request.test_case_ids)} test cases across {len(request.models)} models",
    )


async def run_evaluation_background(
    run_id: UUID,
    test_case_ids: list[UUID],
    model_configs: list,
    evaluator_names: list[str] | None = None,
):
    """Background task to run the evaluation."""
    from app.database import AsyncSessionLocal
    from app.schemas.evaluation import ModelConfig

    async with AsyncSessionLocal() as db:
        configs = [ModelConfig(**m) if isinstance(m, dict) else m for m in model_configs]
        await run_evaluation(db, run_id, test_case_ids, configs)
        if evaluator_names:
            await run_evaluators_on_run(db, run_id, evaluator_names)


@router.get("/runs", response_model=EvaluationRunListResponse)
async def list_evaluation_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    prompt_version: str | None = None,
    status: StatusEnum | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List evaluation runs with optional filtering."""
    query = select(EvaluationRun)

    if prompt_version:
        query = query.where(EvaluationRun.prompt_version == prompt_version)
    if status:
        query = query.where(EvaluationRun.status == status)

    query = query.offset(skip).limit(limit).order_by(EvaluationRun.timestamp.desc())

    result = await db.execute(query)
    runs = result.scalars().all()

    # Get total count
    from sqlalchemy import func
    count_query = select(func.count(EvaluationRun.id))
    if prompt_version:
        count_query = count_query.where(EvaluationRun.prompt_version == prompt_version)
    if status:
        count_query = count_query.where(EvaluationRun.status == status)
    total = await db.execute(count_query)
    total_count = total.scalar() or 0

    return EvaluationRunListResponse(runs=runs, total=total_count)


@router.get("/runs/{run_id}", response_model=EvaluationRunDetailResponse)
async def get_evaluation_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific evaluation run including all outputs."""
    result = await db.execute(
        select(EvaluationRun)
        .options(
            selectinload(EvaluationRun.outputs)
            .selectinload(EvaluationOutput.evaluator_results),
            selectinload(EvaluationRun.outputs)
            .selectinload(EvaluationOutput.annotations),
        )
        .where(EvaluationRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    # Fetch previous completed run for same prompt version (if any)
    prev_result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.prompt_version == run.prompt_version)
        .where(EvaluationRun.status == RunStatus.COMPLETED)
        .where(EvaluationRun.id != run.id)
        .order_by(desc(EvaluationRun.timestamp))
        .options(
            selectinload(EvaluationRun.outputs)
            .selectinload(EvaluationOutput.evaluator_results)
        )
        .limit(1)
    )
    previous_run = prev_result.scalar_one_or_none()

    # Calculate evaluator pass rate deltas
    def summarize_pass_rates(r: EvaluationRun) -> dict[str, float]:
        counts: dict[str, dict[str, int]] = {}
        for output in r.outputs:
            for result in output.evaluator_results:
                entry = counts.setdefault(result.evaluator_name, {'passed': 0, 'total': 0})
                entry['total'] += 1
                if result.passed:
                    entry['passed'] += 1
        rates = {}
        for name, entry in counts.items():
            total = entry['total']
            rates[name] = round((entry['passed'] / total) * 100, 1) if total else 0.0
        return rates

    comparison = None
    if previous_run and run.outputs:
        current_rates = summarize_pass_rates(run)
        previous_rates = summarize_pass_rates(previous_run)
        evaluator_names = set(current_rates.keys()) | set(previous_rates.keys())
        deltas = []
        for name in sorted(evaluator_names):
            current_rate = current_rates.get(name, 0.0)
            previous_rate = previous_rates.get(name, 0.0)
            delta = round(current_rate - previous_rate, 1)
            deltas.append({
                'evaluator_name': name,
                'current_rate': current_rate,
                'previous_rate': previous_rate,
                'delta': delta,
                'regressed': delta < 0,
            })
        comparison = {
            'previous_run_id': str(previous_run.id),
            'previous_timestamp': previous_run.timestamp,
            'deltas': deltas,
            'has_regression': any(item['regressed'] for item in deltas),
        }

    response = EvaluationRunDetailResponse.model_validate(run)
    response_dict = response.model_dump()
    response_dict['comparison'] = comparison
    return response_dict


@router.delete("/runs/{run_id}")
async def delete_evaluation_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete an evaluation run and all its outputs."""
    result = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    await db.delete(run)
    await db.commit()
    return {"success": True, "message": "Evaluation run deleted"}


@router.get("/results")
async def get_aggregated_results(
    prompt_version: str | None = None,
    model: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated evaluation results.
    Useful for comparing performance across models and prompt versions.
    """
    query = select(EvaluationRun).where(EvaluationRun.status == RunStatus.COMPLETED)

    if prompt_version:
        query = query.where(EvaluationRun.prompt_version == prompt_version)

    query = query.options(selectinload(EvaluationRun.outputs))
    result = await db.execute(query)
    runs = result.scalars().all()

    # Aggregate statistics
    stats = {}
    for run in runs:
        for output in run.outputs:
            if model and output.model != model:
                continue

            model_key = output.model
            if model_key not in stats:
                stats[model_key] = {
                    "total_outputs": 0,
                    "total_cost_usd": 0.0,
                    "total_latency_ms": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "error_count": 0,
                }

            stats[model_key]["total_outputs"] += 1
            if output.cost_usd:
                stats[model_key]["total_cost_usd"] += output.cost_usd
            if output.latency_ms:
                stats[model_key]["total_latency_ms"] += output.latency_ms
            if output.input_tokens:
                stats[model_key]["total_input_tokens"] += output.input_tokens
            if output.output_tokens:
                stats[model_key]["total_output_tokens"] += output.output_tokens
            if output.error:
                stats[model_key]["error_count"] += 1

    # Calculate averages
    for model_key in stats:
        count = stats[model_key]["total_outputs"]
        if count > 0:
            stats[model_key]["avg_latency_ms"] = stats[model_key]["total_latency_ms"] / count
            stats[model_key]["avg_cost_usd"] = stats[model_key]["total_cost_usd"] / count
            stats[model_key]["error_rate"] = stats[model_key]["error_count"] / count

    return {
        "prompt_version": prompt_version,
        "model_filter": model,
        "statistics": stats,
    }


@router.get("/evaluators")
async def list_available_evaluators():
    """List all available evaluators."""
    return {
        "evaluators": [
            {
                "name": name,
                "description": cls.description if hasattr(cls, 'description') else "",
            }
            for name, cls in EVALUATOR_REGISTRY.items()
        ]
    }


@router.post("/runs/{run_id}/evaluate")
async def run_evaluators(
    run_id: UUID,
    evaluators: list[str] = Query(default=["instruction_adherence", "format_consistency"]),
    db: AsyncSession = Depends(get_db),
):
    """
    Run behavioral evaluators on an existing evaluation run.

    Args:
        run_id: ID of the evaluation run
        evaluators: List of evaluator names to run

    Available evaluators:
    - instruction_adherence: Check if output follows constraints
    - hallucination: Check if claims are grounded in context
    - format_consistency: Validate output format
    - refusal_behavior: Check refusal appropriateness
    - output_stability: Measure output consistency
    """
    # Validate evaluator names
    invalid = [e for e in evaluators if e not in EVALUATOR_REGISTRY]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown evaluators: {invalid}. Available: {list(EVALUATOR_REGISTRY.keys())}"
        )

    try:
        summary = await run_evaluators_on_run(db, run_id, evaluators)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
