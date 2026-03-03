"""Common schemas."""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseBase(BaseModel):
    """Base response model."""

    success: bool = True
    message: Optional[str] = None


class DataResponse(ResponseBase, Generic[T]):
    """Generic data response."""

    data: T


class ListResponse(ResponseBase, Generic[T]):
    """Generic list response."""

    data: List[T]
    total: int = 0
    page: int = 1
    page_size: int = 20


class ErrorResponse(ResponseBase):
    """Error response model."""

    success: bool = False
    error_code: str = "UNKNOWN_ERROR"
    details: Optional[Dict[str, Any]] = None


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TimestampMixin:
    """Timestamp mixin (not a Pydantic model, just fields)."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class HealthCheck(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: Dict[str, str] = Field(default_factory=dict)
