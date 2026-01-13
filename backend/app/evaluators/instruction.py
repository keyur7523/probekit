import json
import re
from typing import Any
from app.evaluators.base import BaseEvaluator, EvaluationContext, EvaluatorOutput


class InstructionAdherenceEvaluator(BaseEvaluator):
    """
    Evaluates if model output follows explicit instructions/constraints.

    Checks:
    - Valid JSON (if required)
    - Required fields present
    - Length constraints (character/word limits)
    - Forbidden terms absent
    - Pattern matching (regex)
    """

    name = "instruction_adherence"
    description = "Checks if output follows structural and content constraints"

    def __init__(
        self,
        require_json: bool = False,
        required_fields: list[str] | None = None,
        max_length: int | None = None,
        min_length: int | None = None,
        forbidden_terms: list[str] | None = None,
        required_terms: list[str] | None = None,
        pattern: str | None = None,
    ):
        self.require_json = require_json
        self.required_fields = required_fields or []
        self.max_length = max_length
        self.min_length = min_length
        self.forbidden_terms = forbidden_terms or []
        self.required_terms = required_terms or []
        self.pattern = pattern

    async def evaluate(self, context: EvaluationContext) -> EvaluatorOutput:
        output = context.output
        issues = []
        checks_passed = 0
        total_checks = 0

        # Merge instruction_spec from context with instance config
        spec = context.instruction_spec or {}
        max_length = spec.get('max_tokens') or self.max_length
        min_length = self.min_length
        forbidden_terms = spec.get('forbidden_terms') or self.forbidden_terms
        required_terms = spec.get('required_terms') or self.required_terms
        pattern = spec.get('regex_match') or self.pattern
        allow_markdown = spec.get('allow_markdown', True)
        allow_code_blocks = spec.get('allow_code_blocks', True)

        # Check 1: JSON validity
        if self.require_json or context.expected_structure:
            total_checks += 1
            json_valid, json_data, json_error = self._check_json(output)
            if json_valid:
                checks_passed += 1
            else:
                issues.append(f"Invalid JSON: {json_error}")

            # Check required fields if JSON is valid
            required_fields = self.required_fields
            if not required_fields and context.expected_structure:
                required_fields = context.expected_structure.get("required", [])

            if json_valid and required_fields:
                total_checks += 1
                missing = self._check_required_fields(json_data, required_fields)
                if not missing:
                    checks_passed += 1
                else:
                    issues.append(f"Missing required fields: {missing}")

        # Check 2: Length constraints
        if max_length is not None:
            total_checks += 1
            if len(output) <= max_length:
                checks_passed += 1
            else:
                issues.append(f"Output too long: {len(output)} > {max_length}")

        if min_length is not None:
            total_checks += 1
            if len(output) >= min_length:
                checks_passed += 1
            else:
                issues.append(f"Output too short: {len(output)} < {min_length}")

        # Check 3: Forbidden terms
        if forbidden_terms:
            total_checks += 1
            found_forbidden = self._check_forbidden_terms_list(output, forbidden_terms)
            if not found_forbidden:
                checks_passed += 1
            else:
                issues.append(f"Contains forbidden terms: {found_forbidden}")

        # Check 4: Required terms
        if required_terms:
            total_checks += 1
            missing_required = self._check_required_terms_list(output, required_terms)
            if not missing_required:
                checks_passed += 1
            else:
                issues.append(f"Missing required terms: {missing_required}")

        # Check 5: Pattern matching
        if pattern:
            total_checks += 1
            if re.search(pattern, output, re.IGNORECASE):
                checks_passed += 1
            else:
                issues.append(f"Does not match required pattern: {pattern}")

        # Check 6: Markdown formatting
        if not allow_markdown:
            total_checks += 1
            markdown_patterns = [r'#{1,6}\s', r'\*\*.*\*\*', r'\*.*\*', r'^\s*[-*]\s', r'^\s*\d+\.\s']
            has_markdown = any(re.search(p, output, re.MULTILINE) for p in markdown_patterns)
            if not has_markdown:
                checks_passed += 1
            else:
                issues.append("Output contains markdown formatting when not allowed")

        # Check 7: Code blocks
        if not allow_code_blocks:
            total_checks += 1
            has_code_blocks = '```' in output
            if not has_code_blocks:
                checks_passed += 1
            else:
                issues.append("Output contains code blocks when not allowed")

        # Calculate score
        score = checks_passed / total_checks if total_checks > 0 else 1.0
        passed = len(issues) == 0

        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=passed,
            score=score,
            details={
                "checks_passed": checks_passed,
                "total_checks": total_checks,
                "issues": issues,
                "output_length": len(output),
            },
            reasoning="; ".join(issues) if issues else "All instruction checks passed",
        )

    def _check_json(self, output: str) -> tuple[bool, Any, str | None]:
        """Check if output is valid JSON."""
        # Try to extract JSON from output (might be wrapped in markdown)
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', output)
        if json_match:
            output = json_match.group(1)

        try:
            data = json.loads(output.strip())
            return True, data, None
        except json.JSONDecodeError as e:
            return False, None, str(e)

    def _check_required_fields(self, data: Any, required: list[str]) -> list[str]:
        """Check if required fields are present in JSON data."""
        if not isinstance(data, dict):
            return required
        missing = [field for field in required if field not in data]
        return missing

    def _check_forbidden_terms(self, output: str) -> list[str]:
        """Check for forbidden terms in output."""
        return self._check_forbidden_terms_list(output, self.forbidden_terms)

    def _check_forbidden_terms_list(self, output: str, terms: list[str]) -> list[str]:
        """Check for forbidden terms in output."""
        output_lower = output.lower()
        found = [term for term in terms if term.lower() in output_lower]
        return found

    def _check_required_terms(self, output: str) -> list[str]:
        """Check for required terms in output."""
        return self._check_required_terms_list(output, self.required_terms)

    def _check_required_terms_list(self, output: str, terms: list[str]) -> list[str]:
        """Check for required terms in output."""
        output_lower = output.lower()
        missing = [term for term in terms if term.lower() not in output_lower]
        return missing
