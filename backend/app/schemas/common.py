from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class StatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseResponse(BaseModel):
    success: bool = True
    message: str | None = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
