from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import time


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    model: str
    raw_response: Any = None  # Store provider-specific response if needed


class BaseLLMClient(ABC):
    """Abstract base class for LLM API clients."""

    def __init__(self, model_id: str):
        self.model_id = model_id

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt/message
            system: Optional system prompt
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with content, token counts, latency, and cost
        """
        pass

    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost in USD for the given token counts."""
        pass

    def _measure_time(self):
        """Context manager helper for measuring latency."""
        return _TimeMeasure()


class _TimeMeasure:
    """Helper class for measuring execution time."""
    def __init__(self):
        self.start_time = None
        self.elapsed_ms = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = int((time.perf_counter() - self.start_time) * 1000)
