import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=True)
    prompt = Column(Text, nullable=False)
    input = Column(Text, nullable=False)
    expected_structure = Column(JSON, nullable=True)  # JSON schema for validation
    context = Column(Text, nullable=True)  # For hallucination detection
    category = Column(String(100), nullable=True)  # e.g., "safety", "accuracy", "edge_case"

    # Evaluator spec fields (PRD 1.1-1.5)
    instruction_spec = Column(JSON, nullable=True)  # max_tokens, forbidden_terms, required_terms, regex_match
    format_spec = Column(JSON, nullable=True)  # type: json_schema|regex|markdown|csv, spec payload
    stability_params = Column(JSON, nullable=True)  # temperatures[], samples_per_temp
    should_refuse = Column(Boolean, nullable=True)  # Expected refusal behavior for refusal evaluator

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TestCase(id={self.id}, category={self.category})>"
