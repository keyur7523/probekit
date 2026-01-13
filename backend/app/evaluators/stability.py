import re
from collections import Counter
from app.evaluators.base import BaseEvaluator, EvaluationContext, EvaluatorOutput


class StabilityEvaluator(BaseEvaluator):
    """
    Evaluates output stability/consistency across multiple runs.

    Measures:
    - Exact match rate
    - Semantic similarity (Jaccard)
    - Format consistency
    - Key information preservation
    """

    name = "output_stability"
    description = "Measures consistency of outputs across multiple runs"

    def __init__(self, min_similarity: float = 0.7):
        """
        Args:
            min_similarity: Minimum similarity score to pass (0.0 to 1.0)
        """
        self.min_similarity = min_similarity

    async def evaluate(self, context: EvaluationContext) -> EvaluatorOutput:
        """
        Note: This evaluator expects multiple outputs in context.details['outputs']
        or compares the current output against a baseline in context.context
        """
        # For single output comparison against baseline
        if context.context:
            return self._compare_to_baseline(context.output, context.context)

        # If no baseline, just analyze the single output
        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=True,
            score=1.0,
            details={"mode": "single_output", "note": "No baseline for comparison"},
            reasoning="Single output - no stability comparison possible",
        )

    async def evaluate_multiple(self, outputs: list[str]) -> EvaluatorOutput:
        """
        Evaluate stability across multiple outputs.

        Args:
            outputs: List of outputs from same prompt at same/different temperatures
        """
        if len(outputs) < 2:
            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=True,
                score=1.0,
                details={"outputs_count": len(outputs)},
                reasoning="Need at least 2 outputs to measure stability",
            )

        # Calculate pairwise similarities
        similarities = []
        for i in range(len(outputs)):
            for j in range(i + 1, len(outputs)):
                sim = self._jaccard_similarity(outputs[i], outputs[j])
                similarities.append(sim)

        avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0

        # Check exact matches
        exact_matches = sum(1 for i, o1 in enumerate(outputs) for o2 in outputs[i+1:] if o1.strip() == o2.strip())
        total_pairs = len(similarities)

        # Check format consistency
        formats_consistent = self._check_format_consistency(outputs)

        passed = avg_similarity >= self.min_similarity
        score = avg_similarity

        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=passed,
            score=round(score, 3),
            details={
                "outputs_count": len(outputs),
                "avg_similarity": round(avg_similarity, 3),
                "exact_match_pairs": exact_matches,
                "total_pairs": total_pairs,
                "formats_consistent": formats_consistent,
                "min_similarity_threshold": self.min_similarity,
            },
            reasoning=f"Average similarity: {avg_similarity:.1%}" +
                      (" (below threshold)" if not passed else " (stable)"),
        )

    def _compare_to_baseline(self, output: str, baseline: str) -> EvaluatorOutput:
        """Compare single output to a baseline."""
        similarity = self._jaccard_similarity(output, baseline)
        exact_match = output.strip() == baseline.strip()

        passed = similarity >= self.min_similarity
        score = similarity

        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=passed,
            score=round(score, 3),
            details={
                "mode": "baseline_comparison",
                "similarity": round(similarity, 3),
                "exact_match": exact_match,
                "min_similarity_threshold": self.min_similarity,
            },
            reasoning=f"Similarity to baseline: {similarity:.1%}" +
                      (" (exact match)" if exact_match else ""),
        )

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        # Tokenize
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))

        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization."""
        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens

    def _check_format_consistency(self, outputs: list[str]) -> bool:
        """Check if outputs have consistent format."""
        formats = []
        for output in outputs:
            fmt = {
                "has_json": bool(re.search(r'\{[\s\S]*\}', output)),
                "has_bullets": bool(re.search(r'^[\s]*[-*•]', output, re.MULTILINE)),
                "has_numbered": bool(re.search(r'^[\s]*\d+\.', output, re.MULTILINE)),
                "has_headers": bool(re.search(r'^#+\s', output, re.MULTILINE)),
            }
            formats.append(tuple(sorted(fmt.items())))

        # Check if all formats are the same
        return len(set(formats)) == 1
