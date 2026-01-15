import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.models import (
    EvaluationOutput,
    EvaluationRun,
    EvaluatorResult,
    HumanAnnotation,
    RunStatus,
    TestCase,
)


def _load_sample_test_cases() -> list[dict]:
    sample_path = Path(__file__).resolve().parents[1] / "sample_data" / "test_cases.json"
    if not sample_path.exists():
        return []
    return json.loads(sample_path.read_text())


def _fake_output(test_case: TestCase) -> str:
    if test_case.expected_structure:
        return '{"entities":["Acme Corp","BetaSoft"],"summary":"Acme will acquire BetaSoft in an all-stock deal.","confidence":0.82}'
    if test_case.category == "formatting":
        return (
            "# Summary\n"
            "Migration planned next quarter.\n\n"
            "# Risks\n"
            "Potential downtime.\n\n"
            "# Recommendations\n"
            "Stage rollout and monitor closely."
        )
    if test_case.category == "hallucination":
        return "I don't know."
    if test_case.category == "safety":
        return "I can't help with that request, but I can offer tips on home security instead."
    return "Here is a short summary of the input."


def _evaluator_pass(name: str, is_regressed: bool) -> bool:
    # Make one evaluator worse in regressed runs to illustrate behavior
    if is_regressed and name in {"hallucination", "format_consistency"}:
        return False
    return True


async def _seed() -> None:
    await init_db()

    async with AsyncSessionLocal() as db:
        # Ensure test cases exist
        existing = await db.execute(select(TestCase))
        test_cases = existing.scalars().all()
        if not test_cases:
            for item in _load_sample_test_cases():
                db.add(TestCase(**item))
            await db.commit()
            existing = await db.execute(select(TestCase))
            test_cases = existing.scalars().all()

        models = [
            {"model_id": "gpt-4o", "temperature": 0.0, "max_tokens": 512},
            {"model_id": "claude-sonnet-4-20250514", "temperature": 0.0, "max_tokens": 512},
        ]
        evaluators = [
            "instruction_adherence",
            "hallucination",
            "format_consistency",
            "refusal_behavior",
            "output_stability",
        ]

        now = datetime.utcnow()
        prompt_versions = ["v1.0", "v1.1"]
        run_offsets = [timedelta(days=2), timedelta(days=1)]

        for version in prompt_versions:
            for idx, offset in enumerate(run_offsets):
                run = EvaluationRun(
                    prompt_version=version,
                    models=models,
                    status=RunStatus.COMPLETED,
                    timestamp=now - offset,
                    test_case_count=len(test_cases) * len(models),
                    completed_count=len(test_cases) * len(models),
                    total_cost_usd=0.25,
                    total_duration_ms=1250,
                )
                db.add(run)
                await db.flush()

                is_regressed = version == "v1.1" and idx == 1

                for test_case in test_cases:
                    for model in models:
                        output = EvaluationOutput(
                            run_id=run.id,
                            test_case_id=test_case.id,
                            model=model["model_id"],
                            model_response=_fake_output(test_case),
                            latency_ms=420,
                            input_tokens=120,
                            output_tokens=80,
                            cost_usd=0.005,
                        )
                        db.add(output)
                        await db.flush()

                        for evaluator_name in evaluators:
                            passed = _evaluator_pass(evaluator_name, is_regressed)
                            result = EvaluatorResult(
                                output_id=output.id,
                                evaluator_name=evaluator_name,
                                passed=passed,
                                score=1.0 if passed else 0.0,
                                details={"seeded": True},
                                reasoning="Seeded result",
                            )
                            db.add(result)

                        # Add a human annotation for one evaluator on some outputs
                        if test_case.category in {"hallucination", "safety"}:
                            db.add(HumanAnnotation(
                                output_id=output.id,
                                annotation_type="hallucination" if test_case.category == "hallucination" else "refusal_behavior",
                                label="correct" if not is_regressed else "incorrect",
                                notes="Seeded annotation",
                            ))

                await db.commit()


async def main() -> None:
    await _seed()


if __name__ == "__main__":
    asyncio.run(main())
