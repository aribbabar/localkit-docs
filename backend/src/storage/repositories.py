from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func
from sqlmodel import select

from storage.database import Chunk, Database, Document, Source, utc_now


@dataclass(frozen=True)
class SourceRecord:
    id: str
    name: str
    kind: str
    origin: str
    stored_path: str
    status: str
    options: dict[str, Any]


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    source_id: str
    path: str
    title: str | None
    content_hash: str
    chunk_count: int


def _model_to_source(source: Source) -> SourceRecord:
    return SourceRecord(
        id=source.id,
        name=source.name,
        kind=source.kind,
        origin=source.origin,
        stored_path=source.stored_path,
        status=source.status,
        options=json.loads(source.options_json or "{}"),
    )


def _model_to_document(document: Document, chunk_count: int = 0) -> DocumentRecord:
    return DocumentRecord(
        id=document.id,
        source_id=document.source_id,
        path=document.path,
        title=document.title,
        content_hash=document.content_hash,
        chunk_count=chunk_count,
    )


class SourceRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def upsert(self, source: SourceRecord) -> SourceRecord:
        with self.database.session() as session:
            model = session.get(Source, source.id)
            if model is None:
                model = Source(id=source.id)
                session.add(model)
            model.name = source.name
            model.kind = source.kind
            model.origin = source.origin
            model.stored_path = source.stored_path
            model.status = source.status
            model.options_json = json.dumps(source.options, sort_keys=True)
            model.updated_at = utc_now()
        return source

    def list(self) -> list[SourceRecord]:
        with self.database.session() as session:
            sources = session.exec(select(Source).order_by(Source.created_at.desc())).all()
        return [_model_to_source(source) for source in sources]

    def get(self, source_id: str) -> SourceRecord | None:
        with self.database.session() as session:
            source = session.get(Source, source_id)
        return _model_to_source(source) if source else None

    def set_status(self, source_id: str, status: str) -> None:
        with self.database.session() as session:
            source = session.get(Source, source_id)
            if source:
                source.status = status
                source.updated_at = utc_now()

    def remove(self, source_id: str) -> None:
        with self.database.session() as session:
            session.exec(delete(Chunk).where(Chunk.source_id == source_id))
            session.exec(delete(Document).where(Document.source_id == source_id))
            source = session.get(Source, source_id)
            if source:
                session.delete(source)


class DocumentRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def replace_source_chunks(self, source_id: str) -> None:
        with self.database.session() as session:
            session.exec(delete(Chunk).where(Chunk.source_id == source_id))
            session.exec(delete(Document).where(Document.source_id == source_id))

    def add_document(self, document_id: str, source_id: str, path: str, title: str, content_hash: str) -> None:
        with self.database.session() as session:
            session.add(
                Document(
                    id=document_id,
                    source_id=source_id,
                    path=path,
                    title=title,
                    content_hash=content_hash,
                )
            )

    def add_chunk(
        self,
        chunk_id: str,
        document_id: str,
        source_id: str,
        ordinal: int,
        text: str,
        metadata: dict[str, Any],
    ) -> None:
        with self.database.session() as session:
            session.add(
                Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    source_id=source_id,
                    ordinal=ordinal,
                    text=text,
                    metadata_json=json.dumps(metadata, sort_keys=True),
                )
            )

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        with self.database.session() as session:
            chunk = session.get(Chunk, chunk_id)
            document = session.get(Document, chunk.document_id) if chunk else None
        if not chunk or not document:
            return None
        return {
            "id": chunk.id,
            "source_id": chunk.source_id,
            "document_id": chunk.document_id,
            "document_path": document.path,
            "document_title": document.title,
            "ordinal": chunk.ordinal,
            "text": chunk.text,
            "metadata": json.loads(chunk.metadata_json or "{}"),
        }

    def source_stats(self, source_id: str) -> dict[str, int]:
        with self.database.session() as session:
            documents = session.exec(
                select(func.count()).select_from(Document).where(Document.source_id == source_id)
            ).one()
            chunks = session.exec(
                select(func.count()).select_from(Chunk).where(Chunk.source_id == source_id)
            ).one()
        return {"documents": int(documents), "chunks": int(chunks)}

    def list_by_source(self, source_id: str) -> list[DocumentRecord]:
        with self.database.session() as session:
            documents = session.exec(
                select(Document).where(Document.source_id == source_id).order_by(Document.path.asc())
            ).all()
            records = []
            for document in documents:
                chunk_count = session.exec(
                    select(func.count()).select_from(Chunk).where(Chunk.document_id == document.id)
                ).one()
                records.append(_model_to_document(document, int(chunk_count)))
        return records

    def get_document(self, document_id: str) -> DocumentRecord | None:
        with self.database.session() as session:
            document = session.get(Document, document_id)
            if not document:
                return None
            chunk_count = session.exec(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
            ).one()
        return _model_to_document(document, int(chunk_count))

    def list_chunks_by_document(self, document_id: str) -> list[dict[str, Any]]:
        with self.database.session() as session:
            chunks = session.exec(
                select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.ordinal.asc())
            ).all()
        return [
            {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "source_id": chunk.source_id,
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "metadata": json.loads(chunk.metadata_json or "{}"),
            }
            for chunk in chunks
        ]
