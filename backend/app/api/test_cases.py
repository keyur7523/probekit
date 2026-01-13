from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db
from app.models import TestCase
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    TestCaseListResponse,
)

router = APIRouter()


@router.post("/", response_model=TestCaseResponse)
async def create_test_case(
    test_case: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new test case."""
    db_test_case = TestCase(**test_case.model_dump())
    db.add(db_test_case)
    await db.commit()
    await db.refresh(db_test_case)
    return db_test_case


@router.get("/", response_model=TestCaseListResponse)
async def list_test_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all test cases with optional filtering."""
    query = select(TestCase)

    if category:
        query = query.where(TestCase.category == category)

    query = query.offset(skip).limit(limit).order_by(TestCase.created_at.desc())

    result = await db.execute(query)
    test_cases = result.scalars().all()

    # Get total count
    count_query = select(func.count(TestCase.id))
    if category:
        count_query = count_query.where(TestCase.category == category)
    total = await db.execute(count_query)
    total_count = total.scalar() or 0

    return TestCaseListResponse(test_cases=test_cases, total=total_count)


@router.get("/{test_case_id}", response_model=TestCaseResponse)
async def get_test_case(
    test_case_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific test case by ID."""
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    return test_case


@router.put("/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(
    test_case_id: UUID,
    update_data: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a test case."""
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(test_case, key, value)

    await db.commit()
    await db.refresh(test_case)
    return test_case


@router.delete("/{test_case_id}")
async def delete_test_case(
    test_case_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a test case."""
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    await db.delete(test_case)
    await db.commit()
    return {"success": True, "message": "Test case deleted"}
