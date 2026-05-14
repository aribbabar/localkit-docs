from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VectorSearchHit:
    chunk_id: str
    score: float
    text: str
    metadata: dict[str, Any]


class ChromaVectorStore:
    def __init__(self, persist_dir: Path, collection_name: str = "localkit_docs") -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - dependency setup failure.
            raise RuntimeError("Chroma is not installed. Run `pip install -e .` in backend/.") from exc

        persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def delete_source(self, source_id: str) -> None:
        self.collection.delete(where={"source_id": source_id})

    def upsert(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return
        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        embedding: list[float],
        limit: int = 8,
        source_id: str | None = None,
        embedding_model: str | None = None,
    ) -> list[VectorSearchHit]:
        where = _metadata_where(source_id, embedding_model)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        hits: list[VectorSearchHit] = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            hits.append(
                VectorSearchHit(
                    chunk_id=str(chunk_id),
                    score=max(0.0, 1.0 - float(distance)),
                    text=str(text),
                    metadata=dict(metadata or {}),
                )
            )
        return hits


class JsonVectorStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def delete_source(self, source_id: str) -> None:
        rows = [row for row in self._load() if row["metadata"].get("source_id") != source_id]
        self._save(rows)

    def upsert(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        rows = {row["id"]: row for row in self._load()}
        for chunk_id, text, embedding, metadata in zip(ids, texts, embeddings, metadatas, strict=True):
            rows[chunk_id] = {
                "id": chunk_id,
                "text": text,
                "embedding": embedding,
                "metadata": metadata,
            }
        self._save(list(rows.values()))

    def search(
        self,
        embedding: list[float],
        limit: int = 8,
        source_id: str | None = None,
        embedding_model: str | None = None,
    ) -> list[VectorSearchHit]:
        hits: list[VectorSearchHit] = []
        for row in self._load():
            metadata = row["metadata"]
            if source_id and metadata.get("source_id") != source_id:
                continue
            if embedding_model and metadata.get("embedding_model") != embedding_model:
                continue
            hits.append(
                VectorSearchHit(
                    chunk_id=row["id"],
                    score=cosine_similarity(embedding, row["embedding"]),
                    text=row["text"],
                    metadata=metadata,
                )
            )
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, rows: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _metadata_where(source_id: str | None, embedding_model: str | None) -> dict[str, Any] | None:
    clauses: list[dict[str, str]] = []
    if source_id:
        clauses.append({"source_id": source_id})
    if embedding_model:
        clauses.append({"embedding_model": embedding_model})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}
