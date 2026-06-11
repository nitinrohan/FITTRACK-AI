"""Common Pydantic schemas used across multiple endpoints.

All response envelopes follow this shape:
  { "status": "ok" | "error", "data": ..., "message": "..." }

Error responses additionally include:
  { "error_code": "MACHINE_READABLE_CODE", "details": [...] }
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    """Generic success response envelope."""

    model_config = ConfigDict(from_attributes=True)

    status: str = "ok"
    data: DataT | None = None
    message: str | None = None


class ErrorDetail(BaseModel):
    """A single validation or application error detail."""

    field: str | None = None
    message: str
    code: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response body."""

    status: str = "error"
    message: str
    error_code: str = "INTERNAL_ERROR"
    details: list[ErrorDetail] = []


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated list response envelope."""

    model_config = ConfigDict(from_attributes=True)

    status: str = "ok"
    data: list[DataT]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool

    @classmethod
    def build(
        cls,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[Any]:
        return cls(
            data=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
            has_prev=page > 1,
        )
