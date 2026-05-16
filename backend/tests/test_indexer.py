from __future__ import annotations

import asyncio
from pathlib import Path

from core.indexer import Indexer
from storage.database import Database
from storage.repositories import DocumentRepository, SourceRecord, SourceRepository


class FakeEmbeddings:
    @property
    def identity(self) -> str:
        return "fake:test"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.deleted_source: str | None = None
        self.metadatas: list[dict[str, str | int]] = []

    def delete_source(self, source_id: str) -> None:
        self.deleted_source = source_id

    def upsert(
        self,
        *,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, str | int]],
    ) -> None:
        self.metadatas.extend(metadatas)


def test_local_index_uses_normalized_file_name_as_document_title(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "serverless-driver.md").write_text(
        "# Runtime Heading\n\nUse the serverless driver.",
        encoding="utf-8",
    )
    database = Database(tmp_path / "localkit.sqlite3")
    try:
        sources = SourceRepository(database)
        documents = DocumentRepository(database)
        source = SourceRecord(
            id="source-1",
            name="Docs",
            kind="local",
            origin=str(root),
            stored_path=str(root),
            status="pending",
            options={},
        )
        sources.upsert(source)
        vector_store = FakeVectorStore()
        indexer = Indexer(sources, documents, FakeEmbeddings(), vector_store)

        asyncio.run(indexer.index_source(source))

        [document] = documents.list_by_source(source.id)
        assert document.title == "Serverless Driver"
        assert vector_store.deleted_source == source.id
    finally:
        database.close()
