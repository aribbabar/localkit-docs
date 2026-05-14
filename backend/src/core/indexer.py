from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from core.ids import stable_id
from core.progress import ProgressCallback
from ingest.chunking import chunk_text
from ingest.files import iter_indexable_files, read_text_file
from storage.embeddings import EmbeddingProvider
from storage.repositories import DocumentRepository, SourceRecord, SourceRepository


class Indexer:
    def __init__(
        self,
        sources: SourceRepository,
        documents: DocumentRepository,
        embeddings: EmbeddingProvider,
        vector_store,
    ) -> None:
        self.sources = sources
        self.documents = documents
        self.embeddings = embeddings
        self.vector_store = vector_store

    async def index_source(
        self,
        source: SourceRecord,
        progress: ProgressCallback | None = None,
    ) -> dict[str, int]:
        root = Path(source.stored_path)
        if not root.exists():
            raise ValueError(f"Stored source path does not exist: {root}")

        self.sources.set_status(source.id, "indexing")
        try:
            return await self._index_source(source, root, progress=progress)
        except Exception:
            self.sources.set_status(source.id, "failed")
            raise

    async def _index_source(
        self,
        source: SourceRecord,
        root: Path,
        progress: ProgressCallback | None = None,
    ) -> dict[str, int]:
        self.documents.replace_source_chunks(source.id)
        self.vector_store.delete_source(source.id)

        chunk_ids: list[str] = []
        chunk_texts: list[str] = []
        metadatas: list[dict[str, str | int]] = []
        document_records: list[dict[str, Any]] = []
        chunk_records: list[dict[str, Any]] = []
        document_count = 0
        file_paths = list(iter_indexable_files(root))
        if progress:
            progress(
                {
                    "phase": "index",
                    "status": "running",
                    "message": "Indexing documents",
                    "current": 0,
                    "total": len(file_paths),
                }
            )

        for file_index, file_path in enumerate(file_paths, start=1):
            relative_path = file_path.relative_to(root).as_posix()
            if progress:
                progress(
                    {
                        "phase": "index",
                        "status": "running",
                        "message": "Reading document",
                        "current": file_index - 1,
                        "total": len(file_paths),
                        "current_item": relative_path,
                    }
                )
            text = read_text_file(file_path)
            content_hash = sha256(text.encode("utf-8")).hexdigest()
            document_id = stable_id(source.id, relative_path, content_hash)
            title = infer_title(text, relative_path)
            document_records.append(
                {
                    "id": document_id,
                    "source_id": source.id,
                    "path": relative_path,
                    "title": title,
                    "content_hash": content_hash,
                }
            )
            document_count += 1

            for chunk in chunk_text(text):
                chunk_id = stable_id(document_id, str(chunk.ordinal), chunk.text)
                chunk_title = chunk.title or title
                metadata = {
                    "source_id": source.id,
                    "document_id": document_id,
                    "path": relative_path,
                    "title": chunk_title,
                    "ordinal": chunk.ordinal,
                    "section_path": list(chunk.path),
                    "types": list(chunk.types),
                    "embedding_model": self.embeddings.identity,
                }
                vector_metadata = {
                    "source_id": source.id,
                    "document_id": document_id,
                    "path": relative_path,
                    "title": chunk_title,
                    "ordinal": chunk.ordinal,
                    "section_path": " > ".join(chunk.path),
                    "types": ",".join(chunk.types),
                    "embedding_model": self.embeddings.identity,
                }
                chunk_records.append(
                    {
                        "id": chunk_id,
                        "document_id": document_id,
                        "source_id": source.id,
                        "ordinal": chunk.ordinal,
                        "text": chunk.text,
                        "metadata": metadata,
                    }
                )
                chunk_ids.append(chunk_id)
                chunk_texts.append(chunk.text)
                metadatas.append(vector_metadata)
            if progress:
                progress(
                    {
                        "phase": "index",
                        "status": "running",
                        "message": "Indexed document",
                        "current": file_index,
                        "total": len(file_paths),
                        "current_item": relative_path,
                    }
                )

        if progress:
            progress(
                {
                    "phase": "store",
                    "status": "running",
                    "message": "Storing chunk metadata and text index",
                    "current": 0,
                    "total": len(chunk_records),
                }
            )
        self.documents.add_index_records(document_records, chunk_records)
        if progress:
            progress(
                {
                    "phase": "store",
                    "status": "running",
                    "message": "Stored chunk metadata and text index",
                    "current": len(chunk_records),
                    "total": len(chunk_records),
                }
            )

        for start in range(0, len(chunk_texts), 32):
            end = start + 32
            if progress:
                progress(
                    {
                        "phase": "embed",
                        "status": "running",
                        "message": "Embedding chunks",
                        "current": start,
                        "total": len(chunk_texts),
                    }
                )
            vectors = await self.embeddings.embed(chunk_texts[start:end])
            self.vector_store.upsert(
                ids=chunk_ids[start:end],
                texts=chunk_texts[start:end],
                embeddings=vectors,
                metadatas=metadatas[start:end],
            )
            if progress:
                progress(
                    {
                        "phase": "embed",
                        "status": "running",
                        "message": "Stored chunk embeddings",
                        "current": min(end, len(chunk_texts)),
                        "total": len(chunk_texts),
                    }
                )

        self.sources.set_status(source.id, "indexed")
        if progress:
            progress(
                {
                    "phase": "complete",
                    "status": "completed",
                    "message": f"Indexed {document_count} documents into {len(chunk_ids)} chunks",
                    "current": len(chunk_texts),
                    "total": len(chunk_texts),
                }
            )
        return {"documents": document_count, "chunks": len(chunk_ids)}


def infer_title(text: str, fallback: str) -> str:
    lines = text.splitlines()
    start_index = 0
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                start_index = index + 1
                break
    for line in lines[start_index:]:
        stripped = line.strip()
        if stripped.startswith(("source_url:", "status_code:", "saved_at:", "title:")):
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
        if stripped and not stripped.startswith(("---", "<!--")):
            return stripped[:90]
    return fallback


def metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True)
