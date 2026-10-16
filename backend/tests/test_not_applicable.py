"""Not-applicable verdicts (passed is None) must not count toward pass rates or sample sizes."""

from httpx import AsyncClient

from app.models import EvaluationOutput, EvaluationRun, EvaluatorResult, RunStatus, TestCase
from app.services.evaluator_runner import run_evaluators_on_output


async def _run_with_results(session, verdicts: list[bool | None], category: str = "summarization"):
    test_case = TestCase(prompt="p", input="i", category=category)
    session.add(test_case)
    await session.flush()
    run = EvaluationRun(prompt_version="v1", models=[{"model_id": "gpt-4o"}], status=RunStatus.COMPLETED)
    session.add(run)
    await session.flush()
    for verdict in verdicts:
        output = EvaluationOutput(run_id=run.id, test_case_id=test_case.id, model="gpt-4o", model_response="r")
        session.add(output)
        await session.flush()
        session.add(EvaluatorResult(output_id=output.id, evaluator_name="format_consistency", passed=verdict))
    await session.commit()
    return run, test_case


async def test_dashboard_excludes_not_applicable(client: AsyncClient, test_session):
    # 3 passes, 1 fail, 4 not applicable -> 75% over n=4, not 37.5% over 8
    await _run_with_results(test_session, [True, True, True, False, None, None, None, None])

    [row] = (await client.get("/api/dashboard/evaluator-breakdown")).json()["data"]
    assert (row["total"], row["passed"], row["failed"], row["pass_rate"]) == (4, 3, 1, 75.0)

    metrics = (await client.get("/api/dashboard/metrics")).json()
    assert metrics["total_evaluator_results"] == 4
    assert metrics["overall_pass_rate"] == 75.0

    [model] = (await client.get("/api/dashboard/model-comparison")).json()["data"]
    assert (model["total_evaluations"], model["pass_rate"]) == (4, 75.0)


async def test_regression_sample_size_excludes_not_applicable(client: AsyncClient, test_session):
    await _run_with_results(test_session, [True] * 5 + [None] * 20)
    run, _ = await _run_with_results(test_session, [True] * 5 + [None] * 20)

    [delta] = (await client.get(f"/api/evaluations/runs/{run.id}")).json()["comparison"]["deltas"]
    assert (delta["previous_n"], delta["current_n"]) == (5, 5)
    assert delta["status"] == "insufficient_data"


async def test_refusal_has_no_expectation_on_hallucination_tests(test_session):
    run, test_case = await _run_with_results(test_session, [], category="hallucination")
    output = EvaluationOutput(run_id=run.id, test_case_id=test_case.id, model="gpt-4o", model_response="I don't know.")
    test_session.add(output)
    await test_session.commit()

    [result] = await run_evaluators_on_output(test_session, output, test_case, ["refusal_behavior"], {})
    assert result.passed is None
    assert result.details["classification"] == "abstention"


async def test_refusal_still_expected_on_safety_tests(test_session):
    run, test_case = await _run_with_results(test_session, [], category="safety")
    output = EvaluationOutput(run_id=run.id, test_case_id=test_case.id, model="gpt-4o", model_response="Sure, here's how.")
    test_session.add(output)
    await test_session.commit()

    [result] = await run_evaluators_on_output(test_session, output, test_case, ["refusal_behavior"], {})
    assert result.passed is False
