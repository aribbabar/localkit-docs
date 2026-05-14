from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from core.search import SearchService
from storage.database import Database
from storage.repositories import DocumentRepository, SourceRecord, SourceRepository
from storage.vector_store import VectorSearchHit


class FakeEmbeddings:
    @property
    def identity(self) -> str:
        return "fake:test"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class FakeVectorStore:
    def __init__(self, hits: list[VectorSearchHit]) -> None:
        self.hits = hits
        self.requested_limit: int | None = None
        self.embedding_model: str | None = None

    def search(
        self,
        embedding: list[float],
        limit: int = 8,
        source_id: str | None = None,
        embedding_model: str | None = None,
    ) -> list[VectorSearchHit]:
        self.requested_limit = limit
        self.embedding_model = embedding_model
        return self.hits[:limit]


@pytest.fixture()
def repositories(tmp_path: Path):
    database = Database(tmp_path / "localkit.sqlite3")
    sources = SourceRepository(database)
    documents = DocumentRepository(database)
    sources.upsert(
        SourceRecord(
            id="source-1",
            name="Python Docs",
            kind="local",
            origin="E:/docs",
            stored_path="E:/stored",
            status="indexed",
            options={},
        )
    )
    try:
        yield sources, documents
    finally:
        database.close()


def test_search_overfetches_and_assembles_adjacent_context(repositories) -> None:
    sources, documents = repositories
    documents.add_document("document-1", "source-1", "guide.md", "Python Guide", "hash")
    for ordinal in range(4):
        documents.add_chunk(
            chunk_id=f"chunk-{ordinal}",
            document_id="document-1",
            source_id="source-1",
            ordinal=ordinal,
            text=f"Chunk {ordinal}",
            metadata=_metadata("document-1", ordinal),
        )

    vector_store = FakeVectorStore(
        [
            _hit("chunk-1", "document-1", 1, 0.80),
            _hit("chunk-2", "document-1", 2, 0.90),
        ]
    )
    service = SearchService(
        FakeEmbeddings(),
        vector_store,
        documents,
        sources,
        overfetch_multiplier=4,
        vector_multiplier=1,
        context_window=1,
        use_fts=False,
    )

    results = asyncio.run(service.search("python", limit=1))

    assert vector_store.requested_limit == 4
    assert vector_store.embedding_model == "fake:test"
    assert len(results) == 1
    assert results[0].chunk_id == "chunk-2"
    assert results[0].text == "Chunk 0\n\nChunk 1\n\nChunk 2\n\nChunk 3"
    assert results[0].score == pytest.approx(0.92)


def test_search_diversifies_documents_before_lower_scoring_same_document_hits(repositories) -> None:
    sources, documents = repositories
    documents.add_document("document-1", "source-1", "one.md", "one.md", "hash-1")
    documents.add_document("document-2", "source-1", "two.md", "two.md", "hash-2")
    for document_id, path, ordinals in [
        ("document-1", "one.md", [0, 8]),
        ("document-2", "two.md", [0]),
    ]:
        for ordinal in ordinals:
            chunk_id = f"{document_id}-chunk-{ordinal}"
            documents.add_chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                source_id="source-1",
                ordinal=ordinal,
                text=f"{document_id} chunk {ordinal}",
                metadata=_metadata(document_id, ordinal, path=path, title=path),
            )

    vector_store = FakeVectorStore(
        [
            _hit("document-1-chunk-0", "document-1", 0, 0.95, path="one.md", title="one.md"),
            _hit("document-1-chunk-8", "document-1", 8, 0.80, path="one.md", title="one.md"),
            _hit("document-2-chunk-0", "document-2", 0, 0.79, path="two.md", title="two.md"),
        ]
    )
    service = SearchService(FakeEmbeddings(), vector_store, documents, sources, use_fts=False)

    results = asyncio.run(service.search("unmatched", limit=2))

    assert [result.document_id for result in results] == ["document-1", "document-2"]


def test_search_uses_fts_to_find_exact_terms_missed_by_vector_search(repositories) -> None:
    sources, documents = repositories
    documents.add_document("document-1", "source-1", "api.md", "API Guide", "hash-1")
    documents.add_document("document-2", "source-1", "other.md", "Other", "hash-2")
    documents.add_chunk(
        chunk_id="chunk-vector",
        document_id="document-2",
        source_id="source-1",
        ordinal=0,
        text="General overview with unrelated wording.",
        metadata=_metadata("document-2", 0, path="other.md", title="Other"),
    )
    documents.add_chunk(
        chunk_id="chunk-fts",
        document_id="document-1",
        source_id="source-1",
        ordinal=0,
        text="Use the retry_budget option to cap retry behavior.",
        metadata=_metadata("document-1", 0, path="api.md", title="API Guide"),
    )

    vector_store = FakeVectorStore(
        [_hit("chunk-vector", "document-2", 0, 0.99, path="other.md", title="Other")]
    )
    service = SearchService(FakeEmbeddings(), vector_store, documents, sources)

    results = asyncio.run(service.search("retry_budget", limit=1))

    assert results[0].chunk_id == "chunk-fts"
    assert "retry_budget" in results[0].text


def _metadata(
    document_id: str,
    ordinal: int,
    *,
    source_id: str = "source-1",
    path: str = "guide.md",
    title: str = "Python Guide",
) -> dict[str, object]:
    return {
        "document_id": document_id,
        "source_id": source_id,
        "path": path,
        "title": title,
        "ordinal": ordinal,
    }


def _hit(
    chunk_id: str,
    document_id: str,
    ordinal: int,
    score: float,
    *,
    path: str = "guide.md",
    title: str = "Python Guide",
) -> VectorSearchHit:
    return VectorSearchHit(
        chunk_id=chunk_id,
        score=score,
        text=f"Raw {chunk_id}",
        metadata=_metadata(document_id, ordinal, path=path, title=title),
    )
