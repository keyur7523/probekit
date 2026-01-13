import json
import re
from typing import Any
from app.evaluators.base import BaseEvaluator, EvaluationContext, EvaluatorOutput


class FormatEvaluator(BaseEvaluator):
    """
    Evaluates if model output matches expected format.

    Supports:
    - JSON Schema validation
    - Markdown structure validation
    - Custom regex patterns
    - Field type checking
    """

    name = "format_consistency"
    description = "Validates output format against expected schema"

    def __init__(
        self,
        expected_format: str = "json",  # "json", "markdown", "text", "custom"
        json_schema: dict[str, Any] | None = None,
        markdown_headers: list[str] | None = None,
        custom_pattern: str | None = None,
    ):
        self.expected_format = expected_format
        self.json_schema = json_schema
        self.markdown_headers = markdown_headers or []
        self.custom_pattern = custom_pattern

    async def evaluate(self, context: EvaluationContext) -> EvaluatorOutput:
        output = context.output

        # Use format_spec from context if provided
        format_spec = context.format_spec or {}
        format_type = format_spec.get('type') or self.expected_format
        spec_payload = format_spec.get('spec')

        # Use expected_structure from context if provided
        schema = self.json_schema or context.expected_structure

        if format_type == "json_schema" or format_type == "json" or schema:
            # spec_payload can be a JSON schema
            json_schema = spec_payload if isinstance(spec_payload, dict) else schema
            return await self._validate_json(output, json_schema)
        elif format_type == "regex":
            # spec_payload is a regex pattern
            pattern = spec_payload if isinstance(spec_payload, str) else self.custom_pattern
            return await self._validate_pattern(output, pattern)
        elif format_type == "markdown":
            # spec_payload can be a list of required headers
            headers = spec_payload if isinstance(spec_payload, list) else self.markdown_headers
            return await self._validate_markdown(output, headers)
        elif format_type == "csv":
            # spec_payload can have expected_columns
            return await self._validate_csv(output, spec_payload or {})
        elif format_type == "custom" and self.custom_pattern:
            return await self._validate_pattern(output, self.custom_pattern)
        else:
            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=True,
                score=1.0,
                details={"format": "text", "validated": False},
                reasoning="No specific format validation configured",
            )

    async def _validate_json(self, output: str, schema: dict[str, Any] | None) -> EvaluatorOutput:
        """Validate JSON format and optionally against schema."""
        issues = []

        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', output)
        json_str = json_match.group(1) if json_match else output

        try:
            data = json.loads(json_str.strip())
        except json.JSONDecodeError as e:
            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=False,
                score=0.0,
                details={"valid_json": False, "error": str(e)},
                reasoning=f"Invalid JSON: {e}",
            )

        # If no schema, just check JSON validity
        if not schema:
            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=True,
                score=1.0,
                details={"valid_json": True, "data_type": type(data).__name__},
                reasoning="Valid JSON format",
            )

        # Validate against schema (simplified validation)
        schema_issues = self._validate_against_schema(data, schema)

        if schema_issues:
            issues.extend(schema_issues)

        passed = len(issues) == 0
        score = 1.0 - (len(issues) * 0.2)  # Deduct 0.2 per issue
        score = max(0.0, score)

        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=passed,
            score=round(score, 3),
            details={
                "valid_json": True,
                "schema_valid": passed,
                "issues": issues,
            },
            reasoning="; ".join(issues) if issues else "JSON matches expected schema",
        )

    def _validate_against_schema(self, data: Any, schema: dict) -> list[str]:
        """Simple JSON schema validation."""
        issues = []

        # Check type
        expected_type = schema.get("type")
        if expected_type:
            type_map = {
                "object": dict,
                "array": list,
                "string": str,
                "number": (int, float),
                "integer": int,
                "boolean": bool,
            }
            expected_python_type = type_map.get(expected_type)
            if expected_python_type and not isinstance(data, expected_python_type):
                issues.append(f"Expected type {expected_type}, got {type(data).__name__}")

        # String constraints
        if isinstance(data, str):
            min_length = schema.get("minLength")
            max_length = schema.get("maxLength")
            pattern = schema.get("pattern")
            if min_length is not None and len(data) < min_length:
                issues.append(f"String length {len(data)} below minimum {min_length}")
            if max_length is not None and len(data) > max_length:
                issues.append(f"String length {len(data)} exceeds maximum {max_length}")
            if pattern and not re.search(pattern, data):
                issues.append(f"String does not match pattern: {pattern}")

        # Numeric constraints
        if isinstance(data, (int, float)):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and data < minimum:
                issues.append(f"Number {data} below minimum {minimum}")
            if maximum is not None and data > maximum:
                issues.append(f"Number {data} above maximum {maximum}")

        # Enum constraint
        if "enum" in schema and data not in schema["enum"]:
            issues.append(f"Value {data} not in enum {schema['enum']}")

        # Check required fields for objects
        if isinstance(data, dict):
            required = schema.get("required", [])
            for field in required:
                if field not in data:
                    issues.append(f"Missing required field: {field}")

            # Check properties
            properties = schema.get("properties", {})
            for field, field_schema in properties.items():
                if field in data:
                    field_issues = self._validate_against_schema(data[field], field_schema)
                    issues.extend([f"{field}.{issue}" for issue in field_issues])

            if schema.get("additionalProperties") is False:
                allowed_fields = set(properties.keys())
                extra_fields = [field for field in data.keys() if field not in allowed_fields]
                for field in extra_fields:
                    issues.append(f"Unexpected field: {field}")

        # Check array items
        if isinstance(data, list):
            items_schema = schema.get("items")
            min_items = schema.get("minItems", 0)
            max_items = schema.get("maxItems")

            if len(data) < min_items:
                issues.append(f"Array has {len(data)} items, minimum is {min_items}")
            if max_items and len(data) > max_items:
                issues.append(f"Array has {len(data)} items, maximum is {max_items}")

            if items_schema:
                for idx, item in enumerate(data):
                    item_issues = self._validate_against_schema(item, items_schema)
                    issues.extend([f"items[{idx}].{issue}" for issue in item_issues])

        return issues

    async def _validate_markdown(self, output: str, required_headers: list[str] | None = None) -> EvaluatorOutput:
        """Validate markdown structure."""
        issues = []
        found_headers = []
        headers_to_check = required_headers or self.markdown_headers

        # Extract headers
        headers = re.findall(r'^(#{1,6})\s+(.+)$', output, re.MULTILINE)
        found_headers = [h[1].strip() for h in headers]

        # Check for required headers
        for required in headers_to_check:
            if not any(required.lower() in h.lower() for h in found_headers):
                issues.append(f"Missing header: {required}")

        passed = len(issues) == 0
        score = 1.0 - (len(issues) / max(len(headers_to_check), 1)) if headers_to_check else 1.0

        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=passed,
            score=round(max(0.0, score), 3),
            details={
                "format": "markdown",
                "headers_found": found_headers,
                "headers_required": headers_to_check,
                "issues": issues,
            },
            reasoning="; ".join(issues) if issues else "Markdown structure valid",
        )

    async def _validate_csv(self, output: str, spec: dict[str, Any]) -> EvaluatorOutput:
        """Validate CSV format."""
        import csv
        import io

        issues = []
        expected_columns = spec.get('columns', [])
        delimiter = spec.get('delimiter', ',')
        has_header = spec.get('has_header', True)

        try:
            reader = csv.reader(io.StringIO(output.strip()), delimiter=delimiter)
            rows = list(reader)

            if not rows:
                return EvaluatorOutput(
                    evaluator_name=self.name,
                    passed=False,
                    score=0.0,
                    details={"format": "csv", "error": "No CSV data found"},
                    reasoning="No CSV data found in output",
                )

            actual_columns = rows[0] if has_header else []

            # Check expected columns
            if expected_columns and has_header:
                for col in expected_columns:
                    if col not in actual_columns:
                        issues.append(f"Missing column: {col}")

            # Check row consistency
            if rows:
                first_row_len = len(rows[0])
                for idx, row in enumerate(rows[1:], start=2):
                    if len(row) != first_row_len:
                        issues.append(f"Row {idx} has {len(row)} columns, expected {first_row_len}")
                        if len(issues) > 5:  # Limit error messages
                            issues.append("... and more row length mismatches")
                            break

            passed = len(issues) == 0
            score = 1.0 - (len(issues) * 0.2)
            score = max(0.0, score)

            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=passed,
                score=round(score, 3),
                details={
                    "format": "csv",
                    "row_count": len(rows),
                    "column_count": len(rows[0]) if rows else 0,
                    "columns": actual_columns,
                    "issues": issues,
                },
                reasoning="; ".join(issues) if issues else "Valid CSV format",
            )

        except csv.Error as e:
            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=False,
                score=0.0,
                details={"format": "csv", "error": str(e)},
                reasoning=f"Invalid CSV: {e}",
            )

    async def _validate_pattern(self, output: str, pattern: str | None = None) -> EvaluatorOutput:
        """Validate against custom regex pattern."""
        pattern_to_use = pattern or self.custom_pattern
        if not pattern_to_use:
            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=True,
                score=1.0,
                details={},
                reasoning="No pattern specified",
            )

        match = re.search(pattern_to_use, output, re.IGNORECASE | re.MULTILINE)
        passed = match is not None

        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=passed,
            score=1.0 if passed else 0.0,
            details={
                "pattern": pattern_to_use,
                "matched": passed,
                "match_text": match.group(0) if match else None,
            },
            reasoning="Pattern matched" if passed else f"Pattern not found: {pattern_to_use}",
        )
