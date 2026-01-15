from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import ConversationRun, ConversationTurn, ConversationEvaluatorResult, RunStatus
from app.schemas.evaluation import ModelConfig
from app.services.evaluation import get_client_for_model
from app.evaluators.verbosity import VerbosityThresholds, evaluate_verbosity_stability


logger = logging.getLogger(__name__)
DEFAULT_TURN_TIMEOUT_S = 120


FALLBACK_QUESTION_RE = re.compile(
    r"\b(clarif(y|ication)|could you|can you|do you mean|which one|what should)\b",
    re.IGNORECASE,
)
FALLBACK_OFFER_RE = re.compile(
    r"\b(can expand|happy to expand|want more detail|offer to expand)\b",
    re.IGNORECASE,
)


def _build_prompt(transcript: str, user_text: str) -> str:
    return f"{transcript}User: {user_text}\nAssistant:"


def _detect_fallback(assistant_text: str) -> bool:
    if not assistant_text:
        return False
    if assistant_text.strip().endswith("?") and FALLBACK_QUESTION_RE.search(assistant_text):
        return True
    if FALLBACK_OFFER_RE.search(assistant_text):
        return True
    return False


def _thresholds_from_parameters(parameters: dict | None) -> VerbosityThresholds:
    if not parameters:
        return VerbosityThresholds()
    thresholds = parameters.get("thresholds")
    if not isinstance(thresholds, dict):
        return VerbosityThresholds()
    return VerbosityThresholds(
        max_drift_slope=thresholds.get("max_drift_slope", 3.0),
        max_growth_ratio=thresholds.get("max_growth_ratio", 1.2),
        max_stddev_ratio=thresholds.get("max_stddev_ratio", 0.35),
        max_fallback_rate=thresholds.get("max_fallback_rate", 0.15),
    )


def _resolve_artifacts_dir(run_id: UUID) -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "artifacts" / str(run_id)


def _write_artifacts(
    run: ConversationRun,
    transcript_entries: list[dict],
    turn_metrics: list[dict],
    eval_output: "EvaluatorOutput",
) -> None:
    artifacts_dir = _resolve_artifacts_dir(run.id)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    transcript_payload = {
        "run_id": str(run.id),
        "condition": run.condition,
        "model_id": run.model,
        "turns": transcript_entries,
    }
    (artifacts_dir / "transcript.json").write_text(
        json.dumps(transcript_payload, indent=2, ensure_ascii=True)
    )

    metrics_payload = {
        "run_id": str(run.id),
        "condition": run.condition,
        "model_id": run.model,
        "turns": turn_metrics,
    }
    (artifacts_dir / "turn_metrics.json").write_text(
        json.dumps(metrics_payload, indent=2, ensure_ascii=True)
    )

    evaluator_payload = {
        "run_id": str(run.id),
        "condition": run.condition,
        "model_id": run.model,
        "results": [
            {
                "evaluator_name": eval_output.evaluator_name,
                "passed": eval_output.passed,
                "score": eval_output.score,
                "details": eval_output.details,
                "reasoning": eval_output.reasoning,
            }
        ],
    }
    (artifacts_dir / "evaluator_results.json").write_text(
        json.dumps(evaluator_payload, indent=2, ensure_ascii=True)
    )

    aggregate_payload = {
        "run_id": str(run.id),
        "condition": run.condition,
        "model_id": run.model,
        "passed": eval_output.passed,
        "score": eval_output.score,
        "reasoning": eval_output.reasoning,
        "metrics": eval_output.details.get("metrics", {}),
        "fallback_rate": eval_output.details.get("fallback_rate"),
        "thresholds": eval_output.details.get("thresholds", {}),
        "checks": eval_output.details.get("checks", {}),
    }
    (artifacts_dir / "aggregate_metrics.json").write_text(
        json.dumps(aggregate_payload, indent=2, ensure_ascii=True)
    )


async def run_conversation(
    db: AsyncSession,
    run_id: UUID,
    turns: list[str],
    model_config: ModelConfig,
    system_prompt: str | None,
    parameters: dict | None,
) -> None:
    result = await db.execute(select(ConversationRun).where(ConversationRun.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        return

    run.status = RunStatus.RUNNING
    await db.commit()

    client = get_client_for_model(model_config)
    transcript = ""
    total_cost = 0.0
    total_duration = 0
    completed = 0
    output_tokens: list[int] = []
    fallback_used: list[bool] = []
    transcript_entries: list[dict] = []
    turn_metrics: list[dict] = []
    turn_timeout_s = DEFAULT_TURN_TIMEOUT_S
    if parameters and isinstance(parameters.get("turn_timeout_s"), (int, float)):
        turn_timeout_s = int(parameters["turn_timeout_s"])

    try:
        for index, user_text in enumerate(turns):
            prompt = _build_prompt(transcript, user_text)
            response = await asyncio.wait_for(
                client.generate(
                    prompt=prompt,
                    system=system_prompt,
                    temperature=model_config.temperature,
                    max_tokens=model_config.max_tokens,
                ),
                timeout=turn_timeout_s,
            )

            assistant_text = response.content
            fallback_flag = _detect_fallback(assistant_text)

            turn = ConversationTurn(
                run_id=run_id,
                turn_index=index,
                condition=run.condition,
                model_id=run.model,
                user_text=user_text,
                assistant_text=assistant_text,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                cost_usd=response.cost_usd,
                fallback_used=fallback_flag,
            )
            db.add(turn)

            transcript = f"{transcript}User: {user_text}\nAssistant: {assistant_text}\n"
            transcript_entries.append({
                "turn_index": index,
                "user_text": user_text,
                "assistant_text": assistant_text,
            })
            turn_metrics.append({
                "turn_index": index,
                "condition": run.condition,
                "model_id": run.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
                "cost_usd": response.cost_usd,
                "fallback_used": fallback_flag,
            })

            total_cost += response.cost_usd or 0.0
            total_duration += response.latency_ms or 0
            completed += 1
            output_tokens.append(response.output_tokens or 0)
            fallback_used.append(fallback_flag)

            await db.commit()

        run.status = RunStatus.COMPLETED
        run.total_cost_usd = total_cost
        run.total_duration_ms = total_duration
        run.completed_count = completed
        run.turn_count = len(turns)
        await db.commit()

        thresholds = _thresholds_from_parameters(parameters)
        eval_output = evaluate_verbosity_stability(output_tokens, fallback_used, thresholds)
        eval_result = ConversationEvaluatorResult(
            run_id=run_id,
            evaluator_name=eval_output.evaluator_name,
            passed=eval_output.passed,
            score=eval_output.score,
            details=eval_output.details,
            reasoning=eval_output.reasoning,
        )
        db.add(eval_result)
        await db.commit()
        try:
            _write_artifacts(run, transcript_entries, turn_metrics, eval_output)
        except Exception:
            logger.exception("Failed to write conversation artifacts", extra={"run_id": str(run_id)})

    except asyncio.TimeoutError:
        run.status = RunStatus.FAILED
        run.error_message = f"Turn timed out after {turn_timeout_s}s"
        await db.commit()
        raise
    except Exception as exc:
        run.status = RunStatus.FAILED
        run.error_message = str(exc)
        await db.commit()
        raise
