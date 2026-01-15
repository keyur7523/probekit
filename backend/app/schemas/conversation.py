from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Any

from app.schemas.common import StatusEnum
from app.schemas.evaluation import ModelConfig


class ConversationRunCreate(BaseModel):
    condition: str = Field(..., description="Experiment condition (baseline, naive, budgeted, verbatim)")
    model: ModelConfig
    turns: list[str] = Field(..., description="Ordered user turns for the conversation")
    system_prompt: str | None = Field(None, description="System prompt template for the run")
    intent_id: str | None = Field(None, description="Intent template identifier")
    parameters: dict[str, Any] | None = Field(None, description="Run metadata (budgets, thresholds, etc.)")


class TurnEvaluatorResultResponse(BaseModel):
    id: UUID
    evaluator_name: str
    passed: bool | None
    score: float | None
    details: dict[str, Any] | None
    reasoning: str | None

    class Config:
        from_attributes = True


class ConversationTurnResponse(BaseModel):
    id: UUID
    turn_index: int
    condition: str
    model_id: str
    user_text: str
    assistant_text: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    cost_usd: float | None
    fallback_used: bool | None
    evaluator_results: list[TurnEvaluatorResultResponse] = []

    class Config:
        from_attributes = True


class ConversationEvaluatorResultResponse(BaseModel):
    id: UUID
    evaluator_name: str
    passed: bool | None
    score: float | None
    details: dict[str, Any] | None
    reasoning: str | None

    class Config:
        from_attributes = True


class ConversationRunResponse(BaseModel):
    id: UUID
    condition: str
    model: str
    status: StatusEnum
    timestamp: datetime
    intent_id: str | None
    system_prompt: str | None
    parameters: dict[str, Any] | None
    total_cost_usd: float
    total_duration_ms: int
    turn_count: int
    completed_count: int
    error_message: str | None

    class Config:
        from_attributes = True


class ConversationRunDetailResponse(ConversationRunResponse):
    turns: list[ConversationTurnResponse] = []
    evaluator_results: list[ConversationEvaluatorResultResponse] = []


class ConversationRunListResponse(BaseModel):
    runs: list[ConversationRunResponse]
    total: int


class ConversationMetricsResponse(BaseModel):
    run_id: UUID
    condition: str
    model: str
    intent_id: str | None
    metrics: dict[str, Any]
    passed: bool | None


class ConversationMetricsListResponse(BaseModel):
    runs: list[ConversationMetricsResponse]


class ConversationCompareResponse(BaseModel):
    condition_a: str
    condition_b: str
    metrics: dict[str, Any]


class ConversationStartResponse(BaseModel):
    run_id: UUID
    status: StatusEnum
    message: str
