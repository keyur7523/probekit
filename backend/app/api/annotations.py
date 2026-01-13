from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db
from app.models import HumanAnnotation, EvaluationOutput
from app.schemas.annotation import (
    HumanAnnotationCreate,
    HumanAnnotationResponse,
    HumanAnnotationListResponse,
)

router = APIRouter()


@router.post("/", response_model=HumanAnnotationResponse)
async def create_annotation(
    annotation: HumanAnnotationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new human annotation for an evaluation output."""
    result = await db.execute(
        select(EvaluationOutput.id).where(EvaluationOutput.id == annotation.output_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Evaluation output not found")

    db_annotation = HumanAnnotation(**annotation.model_dump())
    db.add(db_annotation)
    await db.commit()
    await db.refresh(db_annotation)
    return db_annotation


@router.get("/", response_model=HumanAnnotationListResponse)
async def list_annotations(
    output_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List human annotations with optional filtering by output_id."""
    query = select(HumanAnnotation)
    count_query = select(func.count(HumanAnnotation.id))

    if output_id:
        query = query.where(HumanAnnotation.output_id == output_id)
        count_query = count_query.where(HumanAnnotation.output_id == output_id)

    query = query.offset(skip).limit(limit).order_by(HumanAnnotation.created_at.desc())

    result = await db.execute(query)
    annotations = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return HumanAnnotationListResponse(annotations=annotations, total=total)
