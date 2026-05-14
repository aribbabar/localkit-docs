from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, text as sql_text
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


@dataclass(frozen=True)
class TextSearchHit:
    chunk_id: str
    score: float
    text: str
    metadata: dict[str, Any]


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
            session.execute(sql_text("DELETE FROM chunks_fts WHERE source_id = :source_id"), {"source_id": source_id})
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
            session.execute(sql_text("DELETE FROM chunks_fts WHERE source_id = :source_id"), {"source_id": source_id})
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
            title = str(metadata.get("title", ""))
            path = str(metadata.get("path", ""))
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
            session.execute(
                sql_text(
                    """
                    INSERT INTO chunks_fts(chunk_id, source_id, document_id, content, title, path)
                    VALUES (:chunk_id, :source_id, :document_id, :content, :title, :path)
                    """
                ),
                {
                    "chunk_id": chunk_id,
                    "source_id": source_id,
                    "document_id": document_id,
                    "content": text,
                    "title": title,
                    "path": path,
                },
            )

    def add_index_records(
        self,
        documents: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
    ) -> None:
        if not documents and not chunks:
            return

        with self.database.session() as session:
            if documents:
                session.add_all(
                    [
                        Document(
                            id=str(document["id"]),
                            source_id=str(document["source_id"]),
                            path=str(document["path"]),
                            title=str(document["title"]),
                            content_hash=str(document["content_hash"]),
                        )
                        for document in documents
                    ]
                )

            if chunks:
                session.add_all(
                    [
                        Chunk(
                            id=str(chunk["id"]),
                            document_id=str(chunk["document_id"]),
                            source_id=str(chunk["source_id"]),
                            ordinal=int(chunk["ordinal"]),
                            text=str(chunk["text"]),
                            metadata_json=json.dumps(chunk["metadata"], sort_keys=True),
                        )
                        for chunk in chunks
                    ]
                )
                session.execute(
                    sql_text(
                        """
                        INSERT INTO chunks_fts(chunk_id, source_id, document_id, content, title, path)
                        VALUES (:chunk_id, :source_id, :document_id, :content, :title, :path)
                        """
                    ),
                    [
                        {
                            "chunk_id": str(chunk["id"]),
                            "source_id": str(chunk["source_id"]),
                            "document_id": str(chunk["document_id"]),
                            "content": str(chunk["text"]),
                            "title": str(chunk["metadata"].get("title", "")),
                            "path": str(chunk["metadata"].get("path", "")),
                        }
                        for chunk in chunks
                    ],
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

    def search_text(
        self,
        query: str,
        limit: int = 8,
        source_id: str | None = None,
    ) -> list[TextSearchHit]:
        fts_query = escape_fts_query(query)
        if fts_query == '""':
            return []

        source_filter = "AND f.source_id = :source_id" if source_id else ""
        statement = sql_text(
            f"""
            SELECT
                f.chunk_id,
                f.source_id,
                f.document_id,
                f.content,
                f.title,
                f.path,
                c.ordinal,
                c.metadata_json,
                bm25(chunks_fts, 0.0, 0.0, 0.0, 1.0, 10.0, 5.0) AS fts_score
            FROM chunks_fts f
            JOIN chunks c ON c.id = f.chunk_id
            WHERE chunks_fts MATCH :query
              {source_filter}
            ORDER BY fts_score
            LIMIT :limit
            """
        )
        params: dict[str, object] = {"query": fts_query, "limit": limit}
        if source_id:
            params["source_id"] = source_id

        with self.database.session() as session:
            rows = session.execute(statement, params).mappings().all()

        hits: list[TextSearchHit] = []
        for row in rows:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
            metadata.update(
                {
                    "source_id": row["source_id"],
                    "document_id": row["document_id"],
                    "path": row["path"] or metadata.get("path", ""),
                    "title": row["title"] or metadata.get("title", ""),
                    "ordinal": row["ordinal"],
                }
            )
            hits.append(
                TextSearchHit(
                    chunk_id=str(row["chunk_id"]),
                    score=max(0.0, -float(row["fts_score"])),
                    text=str(row["content"] or ""),
                    metadata=metadata,
                )
            )
        return hits


def escape_fts_query(query: str) -> str:
    tokens: list[str] = []
    current: list[str] = []
    in_quote = False

    for char in query:
        if char == '"':
            if current:
                tokens.append("".join(current))
                current = []
            in_quote = not in_quote
        elif char.isspace() and not in_quote:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)

    if current:
        tokens.append("".join(current))

    tokens = [token.strip() for token in tokens if token.strip()]
    if not tokens:
        return '""'

    escaped_tokens = [f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens]
    if len(escaped_tokens) == 1:
        return escaped_tokens[0]

    exact_match = f'"{" ".join(tokens).replace(chr(34), chr(34) * 2)}"'
    return f"{exact_match} OR {' OR '.join(escaped_tokens)}"
