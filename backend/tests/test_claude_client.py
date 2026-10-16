"""Tests for request shaping in the Claude client (no network calls)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.clients.claude import (
    SERVER_FALLBACK_BETA,
    ClaudeClient,
    ClaudeRefusalError,
    accepts_sampling_params,
)


def _response(*blocks, stop_reason="end_turn", stop_details=None):
    return SimpleNamespace(
        content=list(blocks),
        stop_reason=stop_reason,
        stop_details=stop_details,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


def _text(text):
    return SimpleNamespace(type="text", text=text)


@pytest.mark.parametrize('model_id,expected', [
    ('claude-haiku-4-5', True),
    ('claude-haiku-4-5-20251001', True),
    ('claude-sonnet-4-20250514', True),
    ('claude-sonnet-4-6', True),
    ('claude-opus-4-7', False),
    ('claude-sonnet-5', False),
    ('claude-sonnet-5-5', False),
    ('claude-haiku-5-5', False),
    ('claude-opus-5-5', False),
    ('claude-fable-5-1', False),
])
def test_accepts_sampling_params(model_id, expected):
    assert accepts_sampling_params(model_id) is expected


async def test_temperature_sent_via_extra_body(monkeypatch):
    """anthropic 1.x rejects a temperature kwarg; it must go in extra_body."""
    client = ClaudeClient(model_id="claude-haiku-4-5")
    create = AsyncMock(return_value=_response(_text("ok")))
    monkeypatch.setattr(client.client.messages, "create", create)

    result = await client.generate("hi", temperature=0.5, max_tokens=64)

    kwargs = create.call_args.kwargs
    assert "temperature" not in kwargs
    assert kwargs["extra_body"] == {"temperature": 0.5}
    assert "output_config" not in kwargs and "system" not in kwargs
    assert result.content == "ok"
    assert result.cost_usd == round(10 / 1e6 * 1.0 + 5 / 1e6 * 5.0, 6)


async def test_sonnet_5_5_omits_sampling_and_uses_fallback(monkeypatch):
    client = ClaudeClient(model_id="claude-sonnet-5-5")
    create = AsyncMock(return_value=_response(_text("ok")))
    monkeypatch.setattr(client.client.beta.messages, "create", create)

    await client.generate("hi", temperature=0.0, max_tokens=4000, effort="low")

    kwargs = create.call_args.kwargs
    assert "extra_body" not in kwargs and "temperature" not in kwargs
    assert kwargs["output_config"] == {"effort": "low"}
    assert kwargs["betas"] == [SERVER_FALLBACK_BETA]
    assert kwargs["fallbacks"] == "default"
    assert kwargs["model"] == "claude-sonnet-5-5"


async def test_reads_text_after_thinking_block(monkeypatch):
    client = ClaudeClient(model_id="claude-sonnet-5-5")
    thinking = SimpleNamespace(type="thinking", thinking="")
    create = AsyncMock(return_value=_response(thinking, _text("1. Claim"), _text(" two")))
    monkeypatch.setattr(client.client.beta.messages, "create", create)

    result = await client.generate("hi")

    assert result.content == "1. Claim two"


async def test_refusal_raises(monkeypatch):
    client = ClaudeClient(model_id="claude-sonnet-5-5")
    response = _response(stop_reason="refusal", stop_details=SimpleNamespace(category="general_harms"))
    monkeypatch.setattr(client.client.beta.messages, "create", AsyncMock(return_value=response))

    with pytest.raises(ClaudeRefusalError, match="general_harms"):
        await client.generate("hi")


def test_hallucination_judge_model():
    from app.evaluators.hallucination import HallucinationEvaluator

    evaluator = HallucinationEvaluator()
    assert evaluator.client.model_id == "claude-sonnet-5-5"
    assert evaluator.JUDGE_EFFORT == "low"
