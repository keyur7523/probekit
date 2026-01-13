from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Any


class InstructionSpec(BaseModel):
    """Specification for instruction adherence evaluator."""
    max_tokens: int | None = Field(None, description="Maximum allowed tokens in response")
    forbidden_terms: list[str] | None = Field(None, description="Terms that must NOT appear in response")
    required_terms: list[str] | None = Field(None, description="Terms that MUST appear in response")
    regex_match: str | None = Field(None, description="Regex pattern the response must match")
    allow_markdown: bool | None = Field(None, description="Whether markdown formatting is allowed")
    allow_code_blocks: bool | None = Field(None, description="Whether code blocks are allowed")


class FormatSpec(BaseModel):
    """Specification for format consistency evaluator."""
    type: str = Field(..., description="Format type: json_schema, regex, markdown, csv")
    spec: dict[str, Any] | str | None = Field(None, description="Format-specific specification")
    # For json_schema: JSON schema dict
    # For regex: regex pattern string
    # For markdown: list of required headings
    # For csv: column names and types


class StabilityParams(BaseModel):
    """Parameters for stability/determinism evaluator."""
    temperatures: list[float] = Field(default=[0.0, 0.3, 0.7], description="Temperatures to test")
    samples_per_temp: int = Field(default=3, description="Number of samples per temperature")


class TestCaseBase(BaseModel):
    title: str | None = Field(None, description="Short, human-friendly test case title")
    prompt: str = Field(..., description="The prompt template to send to models")
    input: str = Field(..., description="The input/query to fill the prompt")
    expected_structure: dict[str, Any] | None = Field(None, description="JSON schema for expected output structure")
    context: str | None = Field(None, description="Context for hallucination detection")
    category: str | None = Field(None, description="Category tag (e.g., 'safety', 'accuracy')")
    # Evaluator spec fields
    instruction_spec: dict[str, Any] | None = Field(None, description="Specification for instruction adherence checks")
    format_spec: dict[str, Any] | None = Field(None, description="Specification for format consistency checks")
    stability_params: dict[str, Any] | None = Field(None, description="Parameters for stability evaluation")
    should_refuse: bool | None = Field(None, description="Whether model should refuse this request")


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(BaseModel):
    title: str | None = None
    prompt: str | None = None
    input: str | None = None
    expected_structure: dict[str, Any] | None = None
    context: str | None = None
    category: str | None = None
    instruction_spec: dict[str, Any] | None = None
    format_spec: dict[str, Any] | None = None
    stability_params: dict[str, Any] | None = None
    should_refuse: bool | None = None


class TestCaseResponse(TestCaseBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestCaseListResponse(BaseModel):
    test_cases: list[TestCaseResponse]
    total: int
