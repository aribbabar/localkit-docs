from __future__ import annotations

import shutil
from pathlib import Path

from core.ids import slugify, stable_id
from core.progress import ProgressCallback
from ingest.crawler import CrawlOptions, crawl_remote, infer_remote_name
from ingest.files import copy_local_source
from storage.repositories import SourceRecord, SourceRepository


class SourceService:
    def __init__(self, sources: SourceRepository, sources_dir: Path) -> None:
        self.sources = sources
        self.sources_dir = sources_dir

    def add_local(
        self,
        path: Path,
        name: str | None = None,
        overwrite: bool = True,
        progress: ProgressCallback | None = None,
    ) -> SourceRecord:
        source_path = path.expanduser().resolve()
        source_name = name or source_path.name
        source_id = stable_id("local", str(source_path), source_name)
        destination = self.sources_dir / "local" / slugify(source_name, source_id) / "content"
        copy_local_source(source_path, destination, overwrite=overwrite, progress=progress)
        record = SourceRecord(
            id=source_id,
            name=source_name,
            kind="local",
            origin=str(source_path),
            stored_path=str(destination),
            status="pending",
            options={},
        )
        return self.sources.upsert(record)

    async def add_remote(
        self,
        url: str,
        name: str | None = None,
        include: str | None = None,
        exclude: str | None = None,
        max_depth: int = 3,
        max_pages: int = 100,
        delay_seconds: float = 0.15,
        overwrite: bool = True,
        progress: ProgressCallback | None = None,
    ) -> SourceRecord:
        source_name = name or infer_remote_name(url)
        source_id = stable_id("remote", url, source_name)
        project_dir = self.sources_dir / "remote" / slugify(source_name, source_id)
        if project_dir.exists() and overwrite:
            shutil.rmtree(project_dir)
        options = CrawlOptions(
            include=include,
            exclude=exclude,
            max_depth=max_depth,
            max_pages=max_pages,
            delay_seconds=delay_seconds,
        )
        crawl = await crawl_remote(url, project_dir, options, progress=progress)
        record = SourceRecord(
            id=source_id,
            name=source_name,
            kind="remote",
            origin=url,
            stored_path=str(crawl.pages_dir),
            status="pending",
            options={
                "include": include,
                "exclude": exclude,
                "max_depth": max_depth,
                "max_pages": max_pages,
                "delay_seconds": delay_seconds,
                "saved_pages": crawl.saved_pages,
            },
        )
        return self.sources.upsert(record)

    def remove(self, source_id: str) -> bool:
        source = self.sources.get(source_id)
        if not source:
            return False
        stored_path = Path(source.stored_path)
        source_root = stored_path.parent if stored_path.name == "content" else stored_path.parent
        if source_root.exists() and self.sources_dir.resolve() in source_root.resolve().parents:
            shutil.rmtree(source_root)
        self.sources.remove(source_id)
        return True
