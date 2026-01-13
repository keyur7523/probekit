from app.evaluators.base import BaseEvaluator, EvaluationContext, EvaluatorOutput
from app.evaluators.instruction import InstructionAdherenceEvaluator
from app.evaluators.hallucination import HallucinationEvaluator
from app.evaluators.format import FormatEvaluator
from app.evaluators.refusal import RefusalEvaluator
from app.evaluators.stability import StabilityEvaluator

__all__ = [
    "BaseEvaluator",
    "EvaluationContext",
    "EvaluatorOutput",
    "InstructionAdherenceEvaluator",
    "HallucinationEvaluator",
    "FormatEvaluator",
    "RefusalEvaluator",
    "StabilityEvaluator",
]

# Registry of available evaluators
EVALUATOR_REGISTRY = {
    "instruction_adherence": InstructionAdherenceEvaluator,
    "hallucination": HallucinationEvaluator,
    "format_consistency": FormatEvaluator,
    "refusal_behavior": RefusalEvaluator,
    "output_stability": StabilityEvaluator,
}


def get_evaluator(name: str, **kwargs) -> BaseEvaluator:
    """Get an evaluator by name."""
    if name not in EVALUATOR_REGISTRY:
        raise ValueError(f"Unknown evaluator: {name}. Available: {list(EVALUATOR_REGISTRY.keys())}")
    return EVALUATOR_REGISTRY[name](**kwargs)
