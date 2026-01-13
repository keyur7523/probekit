import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class HumanAnnotation(Base):
    """Human annotations for ground truth validation."""
    __tablename__ = "human_annotations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    output_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_outputs.id"), nullable=False)
    annotation_type = Column(String(100), nullable=False)  # e.g., "correctness", "hallucination"
    label = Column(String(100), nullable=False)  # e.g., "correct", "incorrect", "hallucinated"
    notes = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100), nullable=True)  # Optional user identifier

    output = relationship("EvaluationOutput", back_populates="annotations")

    def __repr__(self):
        return f"<HumanAnnotation(id={self.id}, type={self.annotation_type}, label={self.label})>"
