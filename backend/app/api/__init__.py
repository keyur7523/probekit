from fastapi import APIRouter
from app.api import evaluations, test_cases, annotations, dashboard

api_router = APIRouter()
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
api_router.include_router(test_cases.router, prefix="/test-cases", tags=["test-cases"])
api_router.include_router(annotations.router, prefix="/annotations", tags=["annotations"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
