"""The model under test must see the test case's source document."""

from app.models import TestCase
from app.services.evaluation import build_prompt


def test_prompt_includes_context_between_instructions_and_input():
    test_case = TestCase(
        prompt="Answer using only the document.",
        input="Question: What was Q3 growth?",
        context="Q1 growth was 5%. Q2 growth was 7%.",
    )
    assert build_prompt(test_case) == (
        "Answer using only the document.\n\n"
        "Document:\nQ1 growth was 5%. Q2 growth was 7%.\n\n"
        "Input: Question: What was Q3 growth?"
    )


def test_prompt_without_context_is_unchanged():
    test_case = TestCase(prompt="Summarize.", input="Some text.")
    assert build_prompt(test_case) == "Summarize.\n\nInput: Some text."


async def test_generation_and_stability_use_same_prompt(monkeypatch):
    from unittest.mock import AsyncMock
    from app.clients.base import LLMResponse
    from app.models import EvaluationOutput
    from app.schemas.evaluation import ModelConfig
    from app.services import evaluator_runner
    from app.services.evaluation import run_single_evaluation

    test_case = TestCase(prompt="P", input="I", context="DOC", stability_params={"temperatures": [0.0], "samples_per_temp": 1})
    client = AsyncMock()
    client.generate = AsyncMock(return_value=LLMResponse(
        content="r", input_tokens=1, output_tokens=1, latency_ms=1, cost_usd=0.0, model="m",
    ))
    config = ModelConfig(model_id="claude-haiku-4-5")

    await run_single_evaluation(client, test_case, config)
    monkeypatch.setattr(evaluator_runner, "get_client_for_model", lambda _: client)
    await evaluator_runner._run_stability_evaluator(EvaluationOutput(model="claude-haiku-4-5", model_response="r"), test_case, config)

    prompts = [call.kwargs["prompt"] for call in client.generate.call_args_list]
    assert prompts == [build_prompt(test_case)] * 2
    assert "Document:\nDOC" in prompts[0]
