import anthropic
from app.clients.base import BaseLLMClient, LLMResponse, _TimeMeasure
from app.clients.retry import retry_with_backoff, RetryConfig
from app.config import get_settings

settings = get_settings()

# Model pricing (USD per 1M tokens)
CLAUDE_PRICING = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-7-sonnet-20250219": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet-latest": {"input": 3.0, "output": 15.0},
    "claude-opus-4-5-20251101": {"input": 15.0, "output": 75.0},
    "claude-opus-4-1-20250805": {"input": 15.0, "output": 75.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-3-opus-latest": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
    "claude-3-5-haiku-20241022": {"input": 0.8, "output": 4.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}

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
        **kwargs
    ) -> LLMResponse:
        """Generate a response using Claude with retry logic."""
        timer = _TimeMeasure()
        messages = [{"role": "user", "content": prompt}]

        async def _make_request():
            return await self.client.messages.create(
                model=self.model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or "",
                messages=messages,
            )

        with timer:
            response = await retry_with_backoff(_make_request, config=CLAUDE_RETRY_CONFIG)

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        content = response.content[0].text if response.content else ""

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
