from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx


class EmbeddingProvider(ABC):
    @property
    def identity(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    @property
    def identity(self) -> str:
        return f"ollama:{self.model}"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        normalized_texts = [_normalize_embedding_text(text) for text in texts]
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": normalized_texts},
            )
            response.raise_for_status()
            return _parse_embeddings_payload(response.json(), expected_count=len(texts))


def _normalize_embedding_text(text: str) -> str:
    return text.replace("\n", " ")


def _parse_embeddings_payload(payload: dict[str, Any], expected_count: int) -> list[list[float]]:
    raw_embeddings = payload.get("embeddings")
    if not isinstance(raw_embeddings, list):
        raise ValueError("Ollama embedding response did not include embeddings.")

    embeddings = [[float(value) for value in embedding] for embedding in raw_embeddings]
    if len(embeddings) != expected_count:
        raise ValueError(
            f"Ollama returned {len(embeddings)} embeddings for {expected_count} input texts."
        )
    return embeddings
