from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import UploadFile

from api.schemas import LocalSourceRequest, RemoteSourceRequest, SearchRequest
from core.factory import build_embedding_provider, build_vector_store
from core.ids import slugify, stable_id
from core.indexer import Indexer
from core.progress import ProgressCallback, ProgressEvent
from core.search import SearchService
from core.services import build_container
from core.sources import SourceService
from storage.repositories import SourceRecord


def create_app() -> FastAPI:
    app = FastAPI(title="LocalKit Docs", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    container = build_container()
    embeddings = build_embedding_provider(container)
    vector_store = build_vector_store(container)
    source_service = SourceService(container.sources, container.settings.sources_dir)
    indexer = Indexer(container.sources, container.documents, embeddings, vector_store)
    search_service = SearchService(embeddings, vector_store)
    operations: dict[str, dict[str, object]] = {}

    def report_for(operation_id: str | None) -> ProgressCallback | None:
        if not operation_id:
            return None

        def report(event: ProgressEvent) -> None:
            update_operation(operations, operation_id, event)

        update_operation(
            operations,
            operation_id,
            {"phase": "queued", "status": "running", "message": "Starting", "current": 0},
        )
        return report

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "data_dir": str(container.settings.data_dir),
            "vector_backend": container.settings.vector_backend,
        }

    @app.get("/sources")
    def list_sources() -> list[dict[str, object]]:
        return [source.__dict__ for source in container.sources.list()]

    @app.get("/operations/{operation_id}")
    def get_operation(operation_id: str) -> dict[str, object]:
        return operations.get(
            operation_id,
            {
                "operation_id": operation_id,
                "phase": "queued",
                "status": "running",
                "message": "Waiting for operation to start",
                "current": 0,
                "events": [],
            },
        )

    @app.get("/sources/{source_id}/documents")
    def list_documents(source_id: str) -> list[dict[str, object]]:
        source = container.sources.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found.")
        return [document.__dict__ for document in container.documents.list_by_source(source_id)]

    @app.get("/documents/{document_id}")
    def get_document(document_id: str) -> dict[str, object]:
        document = container.documents.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")
        source = container.sources.get(document.source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found.")
        content = read_stored_document(Path(source.stored_path), document.path)
        return {
            "document": document.__dict__,
            "source": source.__dict__,
            "content": content,
            "chunks": container.documents.list_chunks_by_document(document_id),
        }

    @app.post("/sources/local")
    async def add_local(request: LocalSourceRequest) -> dict[str, object]:
        progress = report_for(request.operation_id)
        try:
            source = source_service.add_local(Path(request.path), request.name, progress=progress)
            stats = await indexer.index_source(source, progress=progress) if request.index else None
            if progress and not request.index:
                progress({"phase": "complete", "status": "completed", "message": "Local docs added"})
            return {"source": source.__dict__, "stats": stats}
        except Exception as exc:  # noqa: BLE001 - surface actionable API error.
            if progress:
                progress({"phase": "failed", "status": "failed", "message": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sources/local/upload")
    async def upload_local_folder(
        request: Request,
        max_files: Annotated[int, Query(ge=1, le=100_000)] = 10_000,
    ) -> dict[str, object]:
        form = await request.form(max_files=max_files)
        files = [item for item in form.getlist("files") if isinstance(item, UploadFile)]
        name = _form_string(form.get("name"))
        should_index = _form_bool(form.get("index"), default=True)
        operation_id = _form_string(form.get("operation_id"))
        progress = report_for(operation_id)
        try:
            if not files:
                raise ValueError("No files were uploaded.")

            relative_paths = [_safe_upload_path(file.filename or "uploaded-file") for file in files]
            source_name = name or _infer_upload_name(relative_paths)
            source_id = stable_id("local-upload", source_name)
            destination = container.settings.sources_dir / "local" / slugify(source_name, source_id) / "content"
            source_root = destination.parent

            if source_root.exists():
                shutil.rmtree(source_root)
            destination.mkdir(parents=True, exist_ok=True)

            if progress:
                progress(
                    {
                        "phase": "upload",
                        "status": "running",
                        "message": "Saving uploaded files",
                        "current": 0,
                        "total": len(files),
                    }
                )
            for file_index, (upload, relative_path) in enumerate(
                zip(files, relative_paths, strict=True),
                start=1,
            ):
                target = (destination / relative_path).resolve()
                if destination.resolve() not in target.parents:
                    raise ValueError(f"Upload path escapes source root: {relative_path.as_posix()}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(await upload.read())
                if progress:
                    progress(
                        {
                            "phase": "upload",
                            "status": "running",
                            "message": "Saved uploaded file",
                            "current": file_index,
                            "total": len(files),
                            "current_item": relative_path.as_posix(),
                        }
                    )

            source = container.sources.upsert(
                SourceRecord(
                    id=source_id,
                    name=source_name,
                    kind="local",
                    origin=f"browser-upload:{source_name}",
                    stored_path=str(destination),
                    status="pending",
                    options={"uploaded_files": len(files)},
                )
            )
            stats = await indexer.index_source(source, progress=progress) if should_index else None
            if progress and not should_index:
                progress({"phase": "complete", "status": "completed", "message": "Local docs uploaded"})
            return {"source": source.__dict__, "stats": stats}
        except Exception as exc:  # noqa: BLE001
            if progress:
                progress({"phase": "failed", "status": "failed", "message": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sources/remote")
    async def add_remote(request: RemoteSourceRequest) -> dict[str, object]:
        progress = report_for(request.operation_id)
        try:
            source = await source_service.add_remote(
                url=request.url,
                name=request.name,
                include=request.include,
                exclude=request.exclude,
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                delay_seconds=request.delay_seconds,
                progress=progress,
            )
            stats = await indexer.index_source(source, progress=progress) if request.index else None
            if progress and not request.index:
                progress({"phase": "complete", "status": "completed", "message": "Remote docs crawled"})
            return {"source": source.__dict__, "stats": stats}
        except Exception as exc:  # noqa: BLE001
            if progress:
                progress({"phase": "failed", "status": "failed", "message": str(exc)})
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sources/{source_id}/index")
    async def index_source(source_id: str, operation_id: str | None = None) -> dict[str, object]:
        progress = report_for(operation_id)
        source = container.sources.get(source_id)
        if not source:
            if progress:
                progress({"phase": "failed", "status": "failed", "message": "Source not found."})
            raise HTTPException(status_code=404, detail="Source not found.")
        stats = await indexer.index_source(source, progress=progress)
        return {"source": source.__dict__, "stats": stats}

    @app.delete("/sources/{source_id}")
    def remove_source(source_id: str) -> dict[str, bool]:
        removed = source_service.remove(source_id)
        vector_store.delete_source(source_id)
        return {"removed": removed}

    @app.post("/search")
    async def search(request: SearchRequest) -> dict[str, object]:
        results = await search_service.search(
            query=request.query,
            limit=request.limit,
            source_id=request.source_id,
        )
        return {"results": [result.__dict__ for result in results]}

    return app


def update_operation(
    operations: dict[str, dict[str, object]],
    operation_id: str,
    event: ProgressEvent,
) -> None:
    operation = operations.setdefault(
        operation_id,
        {
            "operation_id": operation_id,
            "phase": "queued",
            "status": "running",
            "message": "Starting",
            "current": 0,
            "events": [],
        },
    )
    operation.update(event)
    operation["operation_id"] = operation_id
    operation["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    current_item = event.get("current_item")
    if not current_item:
        return

    events = operation.setdefault("events", [])
    if not isinstance(events, list):
        events = []
        operation["events"] = events
    entry = {
        "phase": event.get("phase", operation.get("phase")),
        "message": event.get("message", operation.get("message")),
        "current": event.get("current", operation.get("current")),
        "total": event.get("total", operation.get("total")),
        "current_item": current_item,
    }
    if events and isinstance(events[-1], dict) and events[-1].get("current_item") == current_item:
        events[-1] = entry
    else:
        events.append(entry)
    del events[:-8]


def read_stored_document(root: Path, relative_path: str) -> str:
    root = root.resolve()
    document_path = (root / relative_path).resolve()
    if root not in document_path.parents and document_path != root:
        raise HTTPException(status_code=400, detail="Document path escapes source root.")
    if not document_path.exists() or not document_path.is_file():
        raise HTTPException(status_code=404, detail="Stored document file not found.")
    return document_path.read_text(encoding="utf-8", errors="replace")


def _safe_upload_path(filename: str) -> Path:
    normalized = filename.replace("\\", "/").lstrip("/")
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        raise ValueError("Uploaded file is missing a filename.")
    if any(part in {".", ".."} or ":" in part for part in parts):
        raise ValueError(f"Unsafe upload path: {filename}")
    return Path(*parts)


def _infer_upload_name(relative_paths: list[Path]) -> str:
    first = relative_paths[0]
    if len(first.parts) > 1:
        return first.parts[0]
    return first.stem or "uploaded-docs"


def _form_string(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _form_bool(value: object, default: bool) -> bool:
    if not isinstance(value, str):
        return default
    return value.lower() in {"1", "true", "yes", "on"}


app = create_app()
