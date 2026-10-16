"""API timestamps are UTC-aware so browsers don't read UTC clock times as local."""

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.models import EvaluationOutput, EvaluationRun, EvaluatorResult, HumanAnnotation, RunStatus, TestCase
from app.models.types import UTCDateTime


def test_type_marks_loaded_values_utc():
    column_type = UTCDateTime()
    loaded = column_type.process_result_value(datetime(2026, 10, 16, 22, 33, 10), None)
    assert loaded == datetime(2026, 10, 16, 22, 33, 10, tzinfo=timezone.utc)
    assert column_type.process_result_value(None, None) is None


def test_type_stores_naive_utc():
    column_type = UTCDateTime()
    pacific = timezone(timedelta(hours=-7))
    stored = column_type.process_bind_param(datetime(2026, 10, 16, 15, 33, 10, tzinfo=pacific), None)
    assert stored == datetime(2026, 10, 16, 22, 33, 10) and stored.tzinfo is None
    naive = datetime(2026, 10, 16, 22, 33, 10)
    assert column_type.process_bind_param(naive, None) == naive


async def test_api_timestamps_carry_utc_offset(client: AsyncClient, test_session):
    test_case = TestCase(prompt="p", input="i")
    test_session.add(test_case)
    await test_session.flush()
    run = EvaluationRun(
        prompt_version="v1", models=[{"model_id": "gpt-4o"}], status=RunStatus.COMPLETED,
        timestamp=datetime(2026, 10, 16, 22, 33, 10),
    )
    test_session.add(run)
    await test_session.commit()

    detail = (await client.get(f"/api/evaluations/runs/{run.id}")).json()
    assert detail["timestamp"] in ("2026-10-16T22:33:10Z", "2026-10-16T22:33:10+00:00")

    [case] = (await client.get("/api/test-cases/")).json()["test_cases"]
    assert case["created_at"].endswith(("Z", "+00:00"))

    # Hand-built dashboard responses serialize the same way
    [comparison] = (await client.get("/api/dashboard/regressions")).json()["comparisons"]
    assert comparison["current_run"]["timestamp"] in ("2026-10-16T22:33:10Z", "2026-10-16T22:33:10+00:00")


async def test_agreement_handles_missing_created_at(client: AsyncClient, test_session):
    test_case = TestCase(prompt="p", input="i")
    test_session.add(test_case)
    await test_session.flush()
    run = EvaluationRun(prompt_version="v1", models=[{"model_id": "gpt-4o"}], status=RunStatus.COMPLETED)
    test_session.add(run)
    await test_session.flush()
    output = EvaluationOutput(run_id=run.id, test_case_id=test_case.id, model="gpt-4o", model_response="r")
    test_session.add(output)
    await test_session.flush()
    test_session.add(EvaluatorResult(output_id=output.id, evaluator_name="hallucination", passed=True))
    test_session.add(EvaluatorResult(output_id=output.id, evaluator_name="hallucination", passed=False, created_at=None))
    test_session.add(HumanAnnotation(output_id=output.id, annotation_type="hallucination", label="correct"))
    await test_session.commit()

    response = await client.get("/api/dashboard/annotation-accuracy")
    assert response.status_code == 200
    assert response.json()["data"][0]["n"] == 1
