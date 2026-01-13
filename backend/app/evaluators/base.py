from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from app.models import EvaluatorResult


@dataclass
class EvaluationContext:
    """Context passed to evaluators."""
    output: str  # Model's response
    prompt: str  # Original prompt
    input_text: str  # Test case input
    context: str | None = None  # Source context for hallucination checking
    expected_structure: dict[str, Any] | None = None  # Expected JSON schema
    category: str | None = None  # Test case category
    # Evaluator spec fields (PRD 1.1-1.5)
    instruction_spec: dict[str, Any] | None = None  # For instruction adherence checks
    format_spec: dict[str, Any] | None = None  # For format consistency checks
    stability_params: dict[str, Any] | None = None  # For stability evaluation
    should_refuse: bool | None = None  # Expected refusal behavior


@dataclass
class EvaluatorOutput:
    """Result from an evaluator."""
    evaluator_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    details: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "evaluator_name": self.evaluator_name,
            "passed": self.passed,
            "score": self.score,
            "details": self.details,
            "reasoning": self.reasoning,
        }


class BaseEvaluator(ABC):
    """Abstract base class for all evaluators."""

    name: str = "base"
    description: str = "Base evaluator"

    @abstractmethod
    async def evaluate(self, context: EvaluationContext) -> EvaluatorOutput:
        """
        Evaluate the model output.

        Args:
            context: EvaluationContext with output, prompt, and metadata

        Returns:
            EvaluatorOutput with pass/fail, score, and details
        """
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name})>"
