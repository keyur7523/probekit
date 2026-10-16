"""Local (Ollama) models must be labelled as having no API cost, not shown as $0.00."""

import pytest
from httpx import AsyncClient

from app.clients.ollama import OllamaClient, is_local_model
from app.schemas.evaluation import ModelConfig
from app.services.evaluation import get_client_for_model


@pytest.mark.parametrize('model_id,expected', [
    ('llama3.1', True),
    ('mistral:7b', True),
    ('qwen2.5-coder', True),
    ('claude-sonnet-4-20250514', False),
    ('gpt-4o', False),
    ('o1-mini', False),
    ('demo-gpt-4o', False),
    ('some-unknown-model', False),
])
def test_is_local_model(model_id, expected):
    assert is_local_model(model_id) is expected


@pytest.mark.parametrize('model_id', ['llama3.1', 'gpt-4o', 'claude-haiku-4-5', 'phi3', 'unknown'])
def test_local_flag_matches_client_routing(model_id):
    client = get_client_for_model(ModelConfig(model_id=model_id))
    assert isinstance(client, OllamaClient) is is_local_model(model_id)


async def _seed_run(session, model_ids: list[str]):
    from app.models import EvaluationRun, EvaluationOutput, EvaluatorResult, RunStatus, TestCase

    test_case = TestCase(prompt="p", input="i")
    session.add(test_case)
    await session.flush()
    run = EvaluationRun(
        prompt_version="v1",
        models=[{"model_id": m} for m in model_ids],
        status=RunStatus.COMPLETED,
    )
    session.add(run)
    await session.flush()
    for model_id in model_ids:
        output = EvaluationOutput(
            run_id=run.id, test_case_id=test_case.id, model=model_id, model_response="r",
            cost_usd=0.0 if is_local_model(model_id) else 0.002,
        )
        session.add(output)
        await session.flush()
        session.add(EvaluatorResult(output_id=output.id, evaluator_name="format_consistency", passed=True))
    await session.commit()
    return run


async def test_run_and_output_flags(client: AsyncClient, test_session):
    run = await _seed_run(test_session, ["llama3.1", "gpt-4o"])
    data = (await client.get(f"/api/evaluations/runs/{run.id}")).json()
    assert data["all_models_local"] is False
    assert {o["model"]: o["is_local"] for o in data["outputs"]} == {"llama3.1": True, "gpt-4o": False}

    local_run = await _seed_run(test_session, ["llama3.1"])
    runs = (await client.get("/api/evaluations/runs")).json()["runs"]
    assert {r["id"]: r["all_models_local"] for r in runs} == {str(run.id): False, str(local_run.id): True}


async def test_dashboard_flags(client: AsyncClient, test_session):
    await _seed_run(test_session, ["llama3.1", "gpt-4o"])
    models = (await client.get("/api/dashboard/model-comparison")).json()["data"]
    assert {m["model"]: m["is_local"] for m in models} == {"llama3.1": True, "gpt-4o": False}

    [activity] = (await client.get("/api/dashboard/recent-activity")).json()["activity"]
    assert activity["all_models_local"] is False
