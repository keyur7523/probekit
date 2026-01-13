from openai import AsyncOpenAI
from app.clients.base import BaseLLMClient, LLMResponse, _TimeMeasure
from app.clients.retry import retry_with_backoff, RetryConfig
from app.config import get_settings

settings = get_settings()

# Model pricing (USD per 1M tokens)
OPENAI_PRICING = {
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4-turbo-preview": {"input": 10.0, "output": 30.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-2024-11-20": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.6},
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
}

# Retry configuration for OpenAI API
OPENAI_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""

    def __init__(self, model_id: str = "gpt-4o"):
        super().__init__(model_id)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using OpenAI with retry logic."""
        timer = _TimeMeasure()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async def _make_request():
            return await self.client.chat.completions.create(
                model=self.model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
            )

        with timer:
            response = await retry_with_backoff(_make_request, config=OPENAI_RETRY_CONFIG)

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        content = response.choices[0].message.content or ""

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
        """Calculate cost based on OpenAI pricing."""
        pricing = OPENAI_PRICING.get(self.model_id, {"input": 2.5, "output": 10.0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)
