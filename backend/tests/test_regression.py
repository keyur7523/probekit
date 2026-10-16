"""Tests for the minimum-sample + significance rule on regression detection."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.services.regression import (
    IMPROVED,
    INSUFFICIENT_DATA,
    NO_SIGNIFICANT_CHANGE,
    REGRESSED,
    assess_change,
    two_proportion_p_value,
)


class TestAssessChange:
    def test_small_samples_are_insufficient(self):
        # 2/5 -> 1/5 is a 20-point drop, but far too few samples to judge
        result = assess_change(2, 5, 1, 5)
        assert result['status'] == INSUFFICIENT_DATA
        assert result['p_value'] is None
        assert (result['baseline_n'], result['current_n']) == (5, 5)

    def test_large_significant_drop_is_regression(self):
        # 18/20 -> 10/20: pooled p = 0.7, se = sqrt(0.7*0.3*(1/20+1/20)) = 0.14491,
        # z = -0.4 / 0.14491 = -2.760, two-sided p = 0.00578
        result = assess_change(18, 20, 10, 20)
        assert result['status'] == REGRESSED
        assert result['p_value'] == pytest.approx(0.0058, abs=1e-4)

    def test_significant_rise_is_improvement(self):
        assert assess_change(10, 20, 18, 20)['status'] == IMPROVED

    def test_small_drop_is_not_significant(self):
        # 18/20 -> 16/20: pooled 0.85, se = 0.11292, z = -0.886, p = 0.376
        result = assess_change(18, 20, 16, 20)
        assert result['status'] == NO_SIGNIFICANT_CHANGE
        assert result['p_value'] == pytest.approx(0.3758, abs=1e-4)

    def test_min_samples_boundary(self):
        assert assess_change(18, 20, 10, 20)['status'] == REGRESSED
        assert assess_change(18, 20, 10, 19)['status'] == INSUFFICIENT_DATA
        assert assess_change(18, 20, 10, 20, min_samples=21)['status'] == INSUFFICIENT_DATA

    def test_identical_all_pass_runs(self):
        assert two_proportion_p_value(20, 20, 20, 20) == 1.0
        assert assess_change(20, 20, 20, 20)['status'] == NO_SIGNIFICANT_CHANGE

    def test_alpha_controls_significance(self):
        # 40/50 -> 30/50: z = -2.182, p = 0.0291
        assert assess_change(40, 50, 30, 50)['status'] == REGRESSED
        assert assess_change(40, 50, 30, 50, alpha=0.01)['status'] == NO_SIGNIFICANT_CHANGE


async def _add_run(session, test_case, version: str, passed: int, total: int, minutes_ago: int):
    from app.models import EvaluationRun, EvaluationOutput, EvaluatorResult, RunStatus

    run = EvaluationRun(
        prompt_version=version,
        models=[{"model_id": "gpt-4o"}],
        status=RunStatus.COMPLETED,
        timestamp=datetime.utcnow() - timedelta(minutes=minutes_ago),
    )
    session.add(run)
    await session.flush()
    for i in range(total):
        output = EvaluationOutput(run_id=run.id, test_case_id=test_case.id, model="gpt-4o", model_response="r")
        session.add(output)
        await session.flush()
        session.add(EvaluatorResult(output_id=output.id, evaluator_name="format_consistency", passed=i < passed))
    await session.commit()
    return run


async def _test_case(session):
    from app.models import TestCase

    test_case = TestCase(prompt="p", input="i")
    session.add(test_case)
    await session.commit()
    return test_case


class TestRegressionEndpoints:
    async def test_regressions_small_drop_not_flagged(self, client: AsyncClient, test_session):
        test_case = await _test_case(test_session)
        await _add_run(test_session, test_case, "v1", passed=2, total=5, minutes_ago=10)
        await _add_run(test_session, test_case, "v1", passed=1, total=5, minutes_ago=1)

        [comparison] = (await client.get("/api/dashboard/regressions")).json()["comparisons"]
        [item] = comparison["regressions"]
        assert item["status"] == INSUFFICIENT_DATA
        assert item["regressed"] is False
        assert comparison["has_regression"] is False
        assert comparison["has_insufficient_data"] is True

    async def test_regressions_large_drop_flagged(self, client: AsyncClient, test_session):
        test_case = await _test_case(test_session)
        await _add_run(test_session, test_case, "v1", passed=18, total=20, minutes_ago=10)
        await _add_run(test_session, test_case, "v1", passed=10, total=20, minutes_ago=1)

        [comparison] = (await client.get("/api/dashboard/regressions")).json()["comparisons"]
        [item] = comparison["regressions"]
        assert item["status"] == REGRESSED
        assert item["regressed"] is True
        assert (item["previous_n"], item["current_n"]) == (20, 20)
        assert comparison["has_regression"] is True

    async def test_run_detail_comparison_uses_rule(self, client: AsyncClient, test_session):
        test_case = await _test_case(test_session)
        await _add_run(test_session, test_case, "v1", passed=2, total=5, minutes_ago=10)
        current = await _add_run(test_session, test_case, "v1", passed=1, total=5, minutes_ago=1)

        comparison = (await client.get(f"/api/evaluations/runs/{current.id}")).json()["comparison"]
        [delta] = comparison["deltas"]
        assert delta["delta"] == -20.0
        assert delta["status"] == INSUFFICIENT_DATA
        assert comparison["has_regression"] is False

    async def test_compare_requires_significance(self, client: AsyncClient, test_session):
        test_case = await _test_case(test_session)
        await _add_run(test_session, test_case, "v1", passed=2, total=5, minutes_ago=10)
        await _add_run(test_session, test_case, "v2", passed=1, total=5, minutes_ago=1)

        data = (await client.get("/api/dashboard/compare", params={
            "baseline_version": "v1", "current_version": "v2",
        })).json()
        assert data["has_regressions"] is False
        assert "format_consistency" in data["insufficient_data"]
        assert data["comparison"]["evaluators"]["format_consistency"]["status"] == INSUFFICIENT_DATA

    async def test_compare_flags_significant_drop(self, client: AsyncClient, test_session):
        test_case = await _test_case(test_session)
        await _add_run(test_session, test_case, "v1", passed=18, total=20, minutes_ago=10)
        await _add_run(test_session, test_case, "v2", passed=10, total=20, minutes_ago=1)

        data = (await client.get("/api/dashboard/compare", params={
            "baseline_version": "v1", "current_version": "v2",
        })).json()
        assert data["has_regressions"] is True
        flagged = {r["type"] for r in data["regressions"]}
        assert flagged == {"evaluator", "model", "overall"}
        assert data["insufficient_data"] == []
