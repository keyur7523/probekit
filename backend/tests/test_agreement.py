"""Tests for human-vs-evaluator agreement statistics (hand-computed fixtures)."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.services.agreement import (
    ConfusionMatrix,
    cohens_kappa,
    normalize_label,
    summarize,
    wilson_interval,
)


def _matrix(pp: int, pf: int, fp: int, ff: int) -> ConfusionMatrix:
    return ConfusionMatrix(
        human_pass_auto_pass=pp,
        human_pass_auto_fail=pf,
        human_fail_auto_pass=fp,
        human_fail_auto_fail=ff,
    )


class TestAgreementStats:
    def test_kappa_hand_computed(self):
        # n=50, agreed=35 -> po=0.70; human pass 25/50, auto pass 30/50
        # pe = (25*30 + 25*20) / 2500 = 0.50 -> kappa = (0.70-0.50)/(1-0.50) = 0.40
        assert cohens_kappa(_matrix(20, 5, 10, 15)) == pytest.approx(0.4)

    def test_kappa_perfect_and_chance(self):
        assert cohens_kappa(_matrix(10, 0, 0, 10)) == pytest.approx(1.0)
        # Agreement exactly at chance level: po = pe = 0.5
        assert cohens_kappa(_matrix(5, 5, 5, 5)) == pytest.approx(0.0)

    def test_high_raw_agreement_can_have_low_kappa(self):
        # Imbalanced labels: evaluator always passes, 90% of items are human-pass.
        # Raw agreement is 90% but kappa is 0 -- the evaluator adds nothing beyond chance.
        matrix = _matrix(90, 0, 10, 0)
        assert summarize(matrix)['agreement'] == 90.0
        # pe = (90*100 + 10*0) / 10000 = 0.90 = po
        assert cohens_kappa(matrix) == pytest.approx(0.0)
        # human pass 90, auto pass 99: pe = (90*99 + 10*1) / 10000 = 0.892
        # kappa = (0.89 - 0.892) / (1 - 0.892) = -0.0185
        matrix = _matrix(89, 1, 10, 0)
        assert summarize(matrix)['agreement'] == 89.0
        assert cohens_kappa(matrix) == pytest.approx(-0.002 / 0.108)

    def test_kappa_undefined_when_both_raters_constant(self):
        assert cohens_kappa(_matrix(12, 0, 0, 0)) is None

    def test_wilson_hand_computed(self):
        # 35/50, z=1.96: center = (0.7 + z^2/100) / (1 + z^2/50) = 0.68573,
        # half-width = z * sqrt(0.7*0.3/50 + z^2/10000) / (1 + z^2/50) = 0.12324
        low, high = wilson_interval(35, 50)
        assert low == pytest.approx(0.5625, abs=1e-4)
        assert high == pytest.approx(0.8090, abs=1e-4)

    def test_wilson_zero_successes(self):
        # p=0: low = 0, high = (z^2/n) / (1 + z^2/n) = 0.38415 / 1.38415
        low, high = wilson_interval(0, 10)
        assert low == pytest.approx(0.0, abs=1e-12)
        assert high == pytest.approx(0.27753, abs=1e-5)

    def test_n_zero_returns_nulls(self):
        assert wilson_interval(0, 0) is None
        assert cohens_kappa(ConfusionMatrix()) is None
        summary = summarize(ConfusionMatrix())
        assert summary['n'] == 0
        assert summary['agreement'] is None
        assert summary['agreement_ci_95'] is None
        assert summary['kappa'] is None

    def test_summary_fields(self):
        summary = summarize(_matrix(20, 5, 10, 15))
        assert summary['n'] == 50
        assert summary['agreed'] == 35
        assert summary['agreement'] == 70.0
        assert summary['agreement_ci_95'] == {'low': 56.2, 'high': 80.9}
        assert summary['kappa'] == 0.4
        assert summary['confusion_matrix'] == {
            'human_pass_auto_pass': 20,
            'human_pass_auto_fail': 5,
            'human_fail_auto_pass': 10,
            'human_fail_auto_fail': 15,
        }

    @pytest.mark.parametrize('label,expected', [
        ('correct', True), (' PASS ', True), ('faithful', True),
        ('hallucinated', False), ('Incorrect', False),
        ('halucinated', None), ('maybe', None), ('', None), (None, None),
    ])
    def test_normalize_label(self, label, expected):
        assert normalize_label(label) is expected


class TestAnnotationAccuracyEndpoint:
    async def _output(self, session, evaluator_results: list[bool | None]):
        from app.models import EvaluationRun, EvaluationOutput, EvaluatorResult, RunStatus, TestCase

        test_case = TestCase(prompt="p", input="i")
        session.add(test_case)
        await session.flush()
        run = EvaluationRun(prompt_version="v1", models=[{"model_id": "gpt-4o"}], status=RunStatus.COMPLETED)
        session.add(run)
        await session.flush()
        output = EvaluationOutput(run_id=run.id, test_case_id=test_case.id, model="gpt-4o", model_response="r")
        session.add(output)
        await session.flush()
        start = datetime.utcnow()
        for i, passed in enumerate(evaluator_results):
            session.add(EvaluatorResult(
                output_id=output.id, evaluator_name="hallucination", passed=passed,
                created_at=start + timedelta(seconds=i),
            ))
        await session.flush()
        return output

    async def _annotate(self, session, output, label: str, seconds: int = 0):
        from app.models import HumanAnnotation

        session.add(HumanAnnotation(
            output_id=output.id, annotation_type="hallucination", label=label,
            created_at=datetime.utcnow() + timedelta(seconds=seconds),
        ))
        await session.flush()

    async def test_unrecognized_label_is_reported_not_dropped(self, client: AsyncClient, test_session):
        output = await self._output(test_session, [True])
        await self._annotate(test_session, output, "halucinated")
        await test_session.commit()

        data = (await client.get("/api/dashboard/annotation-accuracy")).json()
        assert data["skipped_labels"] == 1
        assert data["unrecognized_labels"] == ["halucinated"]
        [entry] = data["data"]
        assert entry["n"] == 0
        assert entry["skipped_labels"] == 1
        assert entry["agreement"] is None
        assert entry["kappa"] is None
        assert entry["agreement_ci_95"] is None

    async def test_rerun_evaluator_counts_once_using_latest_verdict(self, client: AsyncClient, test_session):
        # Evaluator run twice on the same output (fail, then pass); human says pass.
        output = await self._output(test_session, [False, True])
        await self._annotate(test_session, output, "correct")
        await test_session.commit()

        [entry] = (await client.get("/api/dashboard/annotation-accuracy")).json()["data"]
        assert entry["n"] == 1
        assert entry["agreed"] == 1
        assert entry["confusion_matrix"]["human_pass_auto_pass"] == 1

    async def test_relabel_uses_latest_human_label(self, client: AsyncClient, test_session):
        output = await self._output(test_session, [True])
        await self._annotate(test_session, output, "correct", seconds=0)
        await self._annotate(test_session, output, "hallucinated", seconds=5)
        await test_session.commit()

        [entry] = (await client.get("/api/dashboard/annotation-accuracy")).json()["data"]
        assert entry["n"] == 1
        assert entry["agreed"] == 0
        assert entry["confusion_matrix"]["human_fail_auto_pass"] == 1

    async def test_unscored_evaluator_result_is_skipped(self, client: AsyncClient, test_session):
        output = await self._output(test_session, [None])
        await self._annotate(test_session, output, "correct")
        await test_session.commit()

        [entry] = (await client.get("/api/dashboard/annotation-accuracy")).json()["data"]
        assert entry["n"] == 0
        assert entry["skipped_unscored"] == 1
        assert entry["agreement"] is None
