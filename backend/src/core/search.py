from __future__ import annotations

from dataclasses import dataclass

from storage.embeddings import EmbeddingProvider


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    score: float
    text: str
    source_id: str
    path: str
    title: str


class SearchService:
    def __init__(self, embeddings: EmbeddingProvider, vector_store) -> None:
        self.embeddings = embeddings
        self.vector_store = vector_store

    async def search(self, query: str, limit: int = 8, source_id: str | None = None) -> list[SearchResult]:
        query_embedding = (await self.embeddings.embed([query]))[0]
        hits = self.vector_store.search(query_embedding, limit=limit, source_id=source_id)
        return [
            SearchResult(
                chunk_id=hit.chunk_id,
                document_id=str(hit.metadata.get("document_id", "")),
                score=hit.score,
                text=hit.text,
                source_id=str(hit.metadata.get("source_id", "")),
                path=str(hit.metadata.get("path", "")),
                title=str(hit.metadata.get("title", "")),
            )
            for hit in hits
        ]
