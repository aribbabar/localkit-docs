from __future__ import annotations

from pydantic import BaseModel, Field


class LocalSourceRequest(BaseModel):
    path: str
    name: str | None = None
    index: bool = True
    operation_id: str | None = None


class RemoteSourceRequest(BaseModel):
    url: str
    name: str | None = None
    include: str | None = Field(default=None, description="Only crawl URLs containing this value.")
    exclude: str | None = Field(default=None, description="Skip URLs containing this value.")
    max_depth: int = 3
    max_pages: int = 100
    delay_seconds: float = 0.15
    index: bool = True
    operation_id: str | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 8
    source_id: str | None = None
