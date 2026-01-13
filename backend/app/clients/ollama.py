import httpx
from app.clients.base import BaseLLMClient, LLMResponse, _TimeMeasure
from app.clients.retry import retry_with_backoff, RetryConfig
from app.config import get_settings

settings = get_settings()

# Retry configuration for Ollama API (shorter delays for local service)
OLLAMA_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True,
)


class OllamaClient(BaseLLMClient):
    """Ollama API client for local models (e.g., Llama 3.1)."""

    def __init__(self, model_id: str = "llama3.1"):
        super().__init__(model_id)
        self.base_url = settings.ollama_base_url

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using Ollama with retry logic."""
        timer = _TimeMeasure()

        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        if system:
            payload["system"] = system

        async def _make_request():
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

        with timer:
            data = await retry_with_backoff(_make_request, config=OLLAMA_RETRY_CONFIG)

        content = data.get("response", "")
        # Ollama provides eval_count (output) and prompt_eval_count (input)
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=timer.elapsed_ms,
            cost_usd=0.0,  # Local models are free
            model=self.model_id,
            raw_response=data,
        )

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Ollama runs locally, so cost is always 0."""
        return 0.0
