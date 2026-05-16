from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

PatternList: TypeAlias = str | list[str] | None


class LocalSourceRequest(BaseModel):
    path: str
    name: str | None = None
    index: bool = True
    operation_id: str | None = None


class RemoteSourceRequest(BaseModel):
    url: str
    name: str | None = None
    include: PatternList = Field(default=None, description="Only crawl URLs matching these patterns.")
    exclude: PatternList = Field(default=None, description="Skip URLs matching these patterns.")
    crawl_scope: Literal["path", "domain"] = Field(
        default="path",
        description="Use 'domain' to crawl any matching page on the starting URL's host.",
    )
    max_depth: int = 3
    max_pages: int = 1000
    delay_seconds: float = 0.15
    index: bool = True
    operation_id: str | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 8
    source_id: str | None = None
    path_filter: str | None = None
