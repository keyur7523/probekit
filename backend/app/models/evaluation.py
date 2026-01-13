import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, Boolean, ForeignKey, Enum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        Index('ix_evaluation_runs_timestamp', 'timestamp'),
        Index('ix_evaluation_runs_prompt_version', 'prompt_version'),
        Index('ix_evaluation_runs_status', 'status'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_version = Column(String(100), nullable=False)
    models = Column(JSON, nullable=False)  # List of models to evaluate
    status = Column(Enum(RunStatus), default=RunStatus.PENDING)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_cost_usd = Column(Float, default=0.0)
    total_duration_ms = Column(Integer, default=0)
    test_case_count = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    outputs = relationship("EvaluationOutput", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<EvaluationRun(id={self.id}, status={self.status})>"


class EvaluationOutput(Base):
    __tablename__ = "evaluation_outputs"
    __table_args__ = (
        Index('ix_evaluation_outputs_run_id', 'run_id'),
        Index('ix_evaluation_outputs_run_model', 'run_id', 'model'),
        Index('ix_evaluation_outputs_test_case_id', 'test_case_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), nullable=False)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_cases.id"), nullable=False)
    model = Column(String(100), nullable=False)  # e.g., "claude-3-5-sonnet-20241022"
    model_response = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("EvaluationRun", back_populates="outputs")
    evaluator_results = relationship("EvaluatorResult", back_populates="output", cascade="all, delete-orphan")
    annotations = relationship("HumanAnnotation", back_populates="output", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<EvaluationOutput(id={self.id}, model={self.model})>"


class EvaluatorResult(Base):
    """Stores results from behavioral evaluators."""
    __tablename__ = "evaluator_results"
    __table_args__ = (
        Index('ix_evaluator_results_output_id', 'output_id'),
        Index('ix_evaluator_results_evaluator_name', 'evaluator_name'),
        Index('ix_evaluator_results_output_evaluator', 'output_id', 'evaluator_name'),
        Index('ix_evaluator_results_passed', 'passed'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    output_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_outputs.id"), nullable=False)
    evaluator_name = Column(String(100), nullable=False)  # e.g., "instruction_adherence"
    passed = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)  # 0.0 - 1.0
    details = Column(JSON, nullable=True)  # Evaluator-specific metadata
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    output = relationship("EvaluationOutput", back_populates="evaluator_results")

    def __repr__(self):
        return f"<EvaluatorResult(id={self.id}, evaluator={self.evaluator_name}, passed={self.passed})>"
