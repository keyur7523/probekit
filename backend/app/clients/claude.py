import anthropic
from app.clients.base import BaseLLMClient, LLMResponse, _TimeMeasure
from app.clients.retry import retry_with_backoff, RetryConfig
from app.config import get_settings

settings = get_settings()

# Model pricing (USD per 1M tokens)
CLAUDE_PRICING = {
    "claude-opus-5-5": {"input": 4.0, "output": 20.0},
    "claude-sonnet-5-5": {"input": 2.0, "output": 10.0},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50},
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-7-sonnet-20250219": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet-latest": {"input": 3.0, "output": 15.0},
    "claude-opus-4-5-20251101": {"input": 15.0, "output": 75.0},
    "claude-opus-4-1-20250805": {"input": 15.0, "output": 75.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-3-opus-latest": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "claude-3-5-haiku-20241022": {"input": 0.8, "output": 4.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}

# Models that reject temperature/top_p/top_k (Opus 4.7+, the 5.x line, Fable, Mythos);
# sampling parameters are only sent to models that still accept them.
NO_SAMPLING_MODEL_PREFIXES = (
    "claude-opus-4-7", "claude-opus-4-8", "claude-opus-5", "claude-sonnet-5",
    "claude-haiku-5", "claude-fable", "claude-mythos",
)

# Models that support the server-side refusal fallback (fallbacks="default")
SERVER_FALLBACK_MODELS = ("claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1")
SERVER_FALLBACK_BETA = "server-side-fallback-2026-07-01"


def accepts_sampling_params(model_id: str) -> bool:
    return not model_id.startswith(NO_SAMPLING_MODEL_PREFIXES)


class ClaudeRefusalError(RuntimeError):
    """The model declined the request (stop_reason == "refusal")."""


# Retry configuration for Claude API
CLAUDE_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API client."""

    def __init__(self, model_id: str = "claude-sonnet-4-20250514"):
        super().__init__(model_id)
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        effort: str | None = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using Claude with retry logic.

        temperature is ignored for models that reject sampling parameters; effort
        (low/medium/high/...) is sent as output_config.effort when given.
        """
        timer = _TimeMeasure()
        request = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            request["system"] = system
        if effort:
            request["output_config"] = {"effort": effort}
        if accepts_sampling_params(self.model_id):
            # anthropic 1.x dropped sampling kwargs from create(); the API still accepts them here
            request["extra_body"] = {"temperature": temperature}

        async def _make_request():
            if self.model_id in SERVER_FALLBACK_MODELS:
                # Server-side refusal fallback: a declined request is re-run on a fallback model
                return await self.client.beta.messages.create(
                    **request, betas=[SERVER_FALLBACK_BETA], fallbacks="default",
                )
            return await self.client.messages.create(**request)

        with timer:
            response = await retry_with_backoff(_make_request, config=CLAUDE_RETRY_CONFIG)

        if response.stop_reason == "refusal":
            category = getattr(getattr(response, "stop_details", None), "category", None)
            raise ClaudeRefusalError(f"{self.model_id} declined the request (category: {category})")

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        # Read text by block type: responses can start with a (possibly empty) thinking block
        content = "".join(block.text for block in response.content if block.type == "text")

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=timer.elapsed_ms,
            cost_usd=self.calculate_cost(input_tokens, output_tokens),
            model=self.model_id,
            raw_response=response,
        )

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on Claude pricing."""
        pricing = CLAUDE_PRICING.get(self.model_id, {"input": 3.0, "output": 15.0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)
