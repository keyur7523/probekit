from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Any
from app.schemas.common import StatusEnum
from app.schemas.annotation import HumanAnnotationResponse


class ModelConfig(BaseModel):
    """Configuration for a specific model in an evaluation run."""
    model_id: str = Field(..., description="Model identifier (e.g., 'claude-sonnet-4-20250514')")
    temperature: float = Field(0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(4096, ge=1, le=100000)


class EvaluationRunCreate(BaseModel):
    prompt_version: str = Field(..., description="Version identifier for the prompt being evaluated")
    test_case_ids: list[UUID] = Field(..., description="List of test case IDs to evaluate")
    models: list[ModelConfig] = Field(..., description="Models to run evaluation against")
    evaluators: list[str] = Field(default=[], description="Evaluators to run (Phase 2)")


class EvaluationRunResponse(BaseModel):
    id: UUID
    prompt_version: str
    models: list[dict[str, Any]]
    status: StatusEnum
    timestamp: datetime
    total_cost_usd: float
    total_duration_ms: int
    test_case_count: int
    completed_count: int
    error_message: str | None
    test_case_titles: list[str] = []

    class Config:
        from_attributes = True


class EvaluatorResultResponse(BaseModel):
    id: UUID
    evaluator_name: str
    passed: bool | None
    score: float | None
    details: dict[str, Any] | None
    reasoning: str | None

    class Config:
        from_attributes = True


class EvaluationOutputResponse(BaseModel):
    id: UUID
    test_case_id: UUID
    test_case_title: str | None = None
    model: str
    model_response: str | None
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    error: str | None
    evaluator_results: list[EvaluatorResultResponse] = []
    annotations: list[HumanAnnotationResponse] = []

    class Config:
        from_attributes = True




class EvaluatorRegressionDelta(BaseModel):
    evaluator_name: str
    current_rate: float
    previous_rate: float
    delta: float
    regressed: bool


class RunComparison(BaseModel):
    previous_run_id: UUID
    previous_timestamp: datetime
    deltas: list[EvaluatorRegressionDelta]
    has_regression: bool


class EvaluationRunDetailResponse(EvaluationRunResponse):
    outputs: list[EvaluationOutputResponse] = []
    comparison: RunComparison | None = None


class EvaluationRunListResponse(BaseModel):
    runs: list[EvaluationRunResponse]
    total: int


class EvaluationStartResponse(BaseModel):
    run_id: UUID
    status: StatusEnum
    message: str
