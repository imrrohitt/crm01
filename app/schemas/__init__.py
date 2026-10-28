"""
Pydantic schemas for request/response validation and serialization only.
"""

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


__all__ = ["PaginationMeta"]
