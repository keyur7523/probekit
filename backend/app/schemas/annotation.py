from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Any


class HumanAnnotationBase(BaseModel):
    output_id: UUID = Field(..., description="Evaluation output ID")
    annotation_type: str = Field(..., description="Annotation type (e.g., correctness, hallucination)")
    label: str = Field(..., description="Annotation label (e.g., correct, incorrect)")
    notes: str | None = Field(None, description="Optional notes")
    extra_data: dict[str, Any] | None = Field(None, description="Optional extra metadata")
    created_by: str | None = Field(None, description="Optional user identifier")


class HumanAnnotationCreate(HumanAnnotationBase):
    pass


class HumanAnnotationResponse(HumanAnnotationBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class HumanAnnotationListResponse(BaseModel):
    annotations: list[HumanAnnotationResponse]
    total: int
