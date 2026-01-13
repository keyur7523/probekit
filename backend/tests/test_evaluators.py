"""Tests for behavioral evaluators."""

import pytest
from unittest.mock import AsyncMock, patch

from app.evaluators import (
    InstructionAdherenceEvaluator,
    HallucinationEvaluator,
    FormatEvaluator,
    RefusalEvaluator,
    StabilityEvaluator,
    get_evaluator,
    EVALUATOR_REGISTRY,
)
from app.evaluators.base import EvaluationContext


class TestInstructionAdherenceEvaluator:
    """Tests for InstructionAdherenceEvaluator."""

    async def test_valid_json_passes(self, evaluation_context_factory):
        """Test that valid JSON output passes."""
        evaluator = InstructionAdherenceEvaluator(require_json=True)
        context = evaluation_context_factory(
            output='{"name": "test", "value": 42}'
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.score == 1.0
        assert "All instruction checks passed" in result.reasoning

    async def test_invalid_json_fails(self, evaluation_context_factory):
        """Test that invalid JSON output fails."""
        evaluator = InstructionAdherenceEvaluator(require_json=True)
        context = evaluation_context_factory(output="not valid json {")
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert result.score == 0.0
        assert "Invalid JSON" in result.reasoning

    async def test_json_in_markdown_extracted(self, evaluation_context_factory):
        """Test that JSON inside markdown code blocks is extracted."""
        evaluator = InstructionAdherenceEvaluator(require_json=True)
        context = evaluation_context_factory(
            output='Here is the result:\n```json\n{"key": "value"}\n```'
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True

    async def test_required_fields_present(self, evaluation_context_factory):
        """Test required fields validation."""
        evaluator = InstructionAdherenceEvaluator(
            require_json=True,
            required_fields=["name", "age"]
        )
        context = evaluation_context_factory(
            output='{"name": "John", "age": 30}'
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True

    async def test_required_fields_missing(self, evaluation_context_factory):
        """Test that missing required fields are caught."""
        evaluator = InstructionAdherenceEvaluator(
            require_json=True,
            required_fields=["name", "age", "email"]
        )
        context = evaluation_context_factory(
            output='{"name": "John"}'
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert "Missing required fields" in result.reasoning

    async def test_max_length_exceeded(self, evaluation_context_factory):
        """Test max length constraint."""
        evaluator = InstructionAdherenceEvaluator(max_length=10)
        context = evaluation_context_factory(
            output="This is a very long response that exceeds the limit"
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert "Output too long" in result.reasoning

    async def test_min_length_not_met(self, evaluation_context_factory):
        """Test min length constraint."""
        evaluator = InstructionAdherenceEvaluator(min_length=100)
        context = evaluation_context_factory(output="Short")
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert "Output too short" in result.reasoning

    async def test_forbidden_terms_detected(self, evaluation_context_factory):
        """Test forbidden terms detection."""
        evaluator = InstructionAdherenceEvaluator(
            forbidden_terms=["password", "secret"]
        )
        context = evaluation_context_factory(
            output="The password is 12345"
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert "forbidden terms" in result.reasoning.lower()

    async def test_required_terms_present(self, evaluation_context_factory):
        """Test required terms validation."""
        evaluator = InstructionAdherenceEvaluator(
            required_terms=["summary", "conclusion"]
        )
        context = evaluation_context_factory(
            output="Here is the summary. In conclusion, the results are positive."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True

    async def test_required_terms_missing(self, evaluation_context_factory):
        """Test that missing required terms are caught."""
        evaluator = InstructionAdherenceEvaluator(
            required_terms=["summary", "conclusion"]
        )
        context = evaluation_context_factory(
            output="Here is the summary without the other term."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert "Missing required terms" in result.reasoning

    async def test_pattern_matching(self, evaluation_context_factory):
        """Test regex pattern matching."""
        evaluator = InstructionAdherenceEvaluator(
            pattern=r"\d{3}-\d{4}"  # Phone number pattern
        )
        context = evaluation_context_factory(
            output="Call us at 555-1234"
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True

    async def test_pattern_not_matched(self, evaluation_context_factory):
        """Test pattern not found."""
        evaluator = InstructionAdherenceEvaluator(
            pattern=r"\d{3}-\d{4}"
        )
        context = evaluation_context_factory(
            output="No phone number here"
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert "pattern" in result.reasoning.lower()


class TestFormatEvaluator:
    """Tests for FormatEvaluator."""

    async def test_valid_json_format(self, evaluation_context_factory):
        """Test valid JSON validation."""
        evaluator = FormatEvaluator(expected_format="json")
        context = evaluation_context_factory(
            output='{"status": "ok", "data": [1, 2, 3]}'
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.details["valid_json"] is True

    async def test_json_schema_validation(self, evaluation_context_factory):
        """Test JSON schema validation."""
        schema = {
            "type": "object",
            "required": ["name", "items"],
            "properties": {
                "name": {"type": "string"},
                "items": {"type": "array", "minItems": 1}
            }
        }
        evaluator = FormatEvaluator(json_schema=schema)
        context = evaluation_context_factory(
            output='{"name": "test", "items": ["a", "b"]}'
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True

    async def test_json_schema_missing_required(self, evaluation_context_factory):
        """Test JSON schema with missing required fields."""
        schema = {
            "type": "object",
            "required": ["name", "value"],
        }
        evaluator = FormatEvaluator(json_schema=schema)
        context = evaluation_context_factory(
            output='{"name": "test"}'
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert "Missing required field" in str(result.details["issues"])

    async def test_markdown_headers(self, evaluation_context_factory):
        """Test markdown header validation."""
        evaluator = FormatEvaluator(
            expected_format="markdown",
            markdown_headers=["Summary", "Details"]
        )
        context = evaluation_context_factory(
            output="# Summary\nThis is the summary.\n\n## Details\nHere are the details."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True

    async def test_markdown_missing_headers(self, evaluation_context_factory):
        """Test markdown with missing headers."""
        evaluator = FormatEvaluator(
            expected_format="markdown",
            markdown_headers=["Summary", "Conclusion"]
        )
        context = evaluation_context_factory(
            output="# Summary\nJust a summary."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert "Missing header" in str(result.details["issues"])

    async def test_custom_pattern(self, evaluation_context_factory):
        """Test custom regex pattern validation."""
        evaluator = FormatEvaluator(
            expected_format="custom",
            custom_pattern=r"^Result:\s+\d+$"
        )
        context = evaluation_context_factory(output="Result: 42")
        result = await evaluator.evaluate(context)

        assert result.passed is True


class TestRefusalEvaluator:
    """Tests for RefusalEvaluator."""

    async def test_detects_refusal(self, evaluation_context_factory):
        """Test refusal detection."""
        evaluator = RefusalEvaluator(expect_refusal=True)
        context = evaluation_context_factory(
            output="I'm sorry, but I can't help with that request."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.details["classification"] == "refusal"

    async def test_detects_abstention(self, evaluation_context_factory):
        """Test abstention detection."""
        evaluator = RefusalEvaluator(expect_refusal=True)
        context = evaluation_context_factory(
            output="I don't have that information available."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.details["classification"] == "abstention"

    async def test_detects_clarification(self, evaluation_context_factory):
        """Test clarification request detection."""
        evaluator = RefusalEvaluator()
        context = evaluation_context_factory(
            output="Could you please clarify what you mean by that?"
        )
        result = await evaluator.evaluate(context)

        assert result.details["classification"] == "clarification"

    async def test_detects_answer(self, evaluation_context_factory):
        """Test normal answer detection."""
        evaluator = RefusalEvaluator(expect_answer=True)
        context = evaluation_context_factory(
            output="The capital of France is Paris."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.details["classification"] == "answer"

    async def test_refusal_with_alternatives(self, evaluation_context_factory):
        """Test refusal with alternatives suggested."""
        evaluator = RefusalEvaluator(expect_refusal=True)
        context = evaluation_context_factory(
            output="I can't help with that. However, I can help you with something else instead."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.details["suggests_alternatives"] is True
        assert result.score == 1.0

    async def test_unexpected_refusal(self, evaluation_context_factory):
        """Test when refusal happens but answer was expected."""
        evaluator = RefusalEvaluator(expect_answer=True, expect_refusal=False)
        context = evaluation_context_factory(
            output="I can't answer that question."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False

    async def test_expected_refusal_missing(self, evaluation_context_factory):
        """Test when answer given but refusal was expected."""
        evaluator = RefusalEvaluator(expect_refusal=True, expect_answer=False)
        context = evaluation_context_factory(
            output="Here is the answer you asked for: 42"
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False


class TestStabilityEvaluator:
    """Tests for StabilityEvaluator."""

    async def test_baseline_comparison_similar(self, evaluation_context_factory):
        """Test comparison with similar baseline."""
        evaluator = StabilityEvaluator(min_similarity=0.5)
        context = evaluation_context_factory(
            output="The quick brown fox jumps over the lazy dog.",
            context="The quick brown fox jumped over the lazy dog."  # baseline
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.score > 0.5

    async def test_baseline_comparison_different(self, evaluation_context_factory):
        """Test comparison with very different baseline."""
        evaluator = StabilityEvaluator(min_similarity=0.8)
        context = evaluation_context_factory(
            output="Hello world, this is completely different.",
            context="The quick brown fox jumps over the lazy dog."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert result.score < 0.8

    async def test_exact_match(self, evaluation_context_factory):
        """Test exact match gives perfect score."""
        evaluator = StabilityEvaluator()
        context = evaluation_context_factory(
            output="Exact same text here.",
            context="Exact same text here."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.score == 1.0
        assert result.details["exact_match"] is True

    async def test_no_baseline_single_output(self, evaluation_context_factory):
        """Test behavior when no baseline provided."""
        evaluator = StabilityEvaluator()
        context = evaluation_context_factory(
            output="Just a single output with no baseline."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.details["mode"] == "single_output"

    async def test_multiple_outputs_stability(self):
        """Test stability across multiple outputs."""
        evaluator = StabilityEvaluator(min_similarity=0.5)
        outputs = [
            "The weather is sunny and warm today in the city.",
            "Today the weather is sunny and warm in the city.",
            "The weather today is sunny and warm in the city.",
        ]
        result = await evaluator.evaluate_multiple(outputs)

        assert result.passed is True
        assert result.details["outputs_count"] == 3
        assert "avg_similarity" in result.details

    async def test_multiple_outputs_unstable(self):
        """Test detection of unstable outputs."""
        evaluator = StabilityEvaluator(min_similarity=0.9)
        outputs = [
            "The answer is 42.",
            "I think the answer might be around 50.",
            "Based on my analysis, the result is approximately 38.",
        ]
        result = await evaluator.evaluate_multiple(outputs)

        assert result.passed is False
        assert result.score < 0.9


class TestHallucinationEvaluator:
    """Tests for HallucinationEvaluator."""

    async def test_no_context_skips(self, evaluation_context_factory):
        """Test that evaluation is skipped when no context provided."""
        evaluator = HallucinationEvaluator()
        context = evaluation_context_factory(
            output="Some response without context.",
            context=None
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.details.get("skipped") is True

    @patch("app.evaluators.hallucination.ClaudeClient")
    async def test_grounded_claims(self, mock_client_class, evaluation_context_factory):
        """Test detection of grounded claims."""
        # Mock the client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock claim extraction
        mock_extraction = AsyncMock()
        mock_extraction.content = "1. The company has 50 employees."

        # Mock verification
        mock_verification = AsyncMock()
        mock_verification.content = "1. [SUPPORTED] - Directly stated in context"

        mock_client.generate = AsyncMock(
            side_effect=[mock_extraction, mock_verification]
        )

        evaluator = HallucinationEvaluator()
        evaluator.client = mock_client

        context = evaluation_context_factory(
            output="The company has 50 employees.",
            context="The company has 50 employees and was founded in 2020."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.details["supported"] == 1
        assert result.details["not_supported"] == 0

    @patch("app.evaluators.hallucination.ClaudeClient")
    async def test_hallucinated_claims(self, mock_client_class, evaluation_context_factory):
        """Test detection of hallucinated claims."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_extraction = AsyncMock()
        mock_extraction.content = "1. The company has 500 employees."

        mock_verification = AsyncMock()
        mock_verification.content = "1. [NOT SUPPORTED] - Context says 50, not 500"

        mock_client.generate = AsyncMock(
            side_effect=[mock_extraction, mock_verification]
        )

        evaluator = HallucinationEvaluator()
        evaluator.client = mock_client

        context = evaluation_context_factory(
            output="The company has 500 employees.",
            context="The company has 50 employees."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is False
        assert result.details["not_supported"] == 1
        assert len(result.details["hallucinations"]) == 1

    @patch("app.evaluators.hallucination.ClaudeClient")
    async def test_no_claims_found(self, mock_client_class, evaluation_context_factory):
        """Test when no factual claims are found."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_extraction = AsyncMock()
        mock_extraction.content = "NO CLAIMS"

        mock_client.generate = AsyncMock(return_value=mock_extraction)

        evaluator = HallucinationEvaluator()
        evaluator.client = mock_client

        context = evaluation_context_factory(
            output="I hope you have a great day!",
            context="Some context here."
        )
        result = await evaluator.evaluate(context)

        assert result.passed is True
        assert result.details["claims_found"] == 0


class TestEvaluatorRegistry:
    """Tests for evaluator registry."""

    def test_all_evaluators_registered(self):
        """Test that all expected evaluators are in the registry."""
        expected = [
            "instruction_adherence",
            "hallucination",
            "format_consistency",
            "refusal_behavior",
            "output_stability",
        ]
        for name in expected:
            assert name in EVALUATOR_REGISTRY

    def test_get_evaluator_valid(self):
        """Test getting a valid evaluator."""
        evaluator = get_evaluator("instruction_adherence")
        assert isinstance(evaluator, InstructionAdherenceEvaluator)

    def test_get_evaluator_invalid(self):
        """Test getting an invalid evaluator raises error."""
        with pytest.raises(ValueError, match="Unknown evaluator"):
            get_evaluator("nonexistent_evaluator")

    def test_get_evaluator_with_kwargs(self):
        """Test getting an evaluator with custom arguments."""
        evaluator = get_evaluator(
            "instruction_adherence",
            require_json=True,
            max_length=500
        )
        assert evaluator.require_json is True
        assert evaluator.max_length == 500
