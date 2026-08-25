"""Shared schemas: generic pagination envelope used by every list endpoint."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(description="Total number of matching records, across all pages")
    page: int = Field(description="Current page number, 1-indexed")
    page_size: int
    pages: int = Field(description="Total number of pages")
