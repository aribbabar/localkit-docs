from __future__ import annotations

import os

from core.services import ServiceContainer
from storage.embeddings import DeterministicEmbeddingProvider, EmbeddingProvider, OllamaEmbeddingProvider
from storage.vector_store import ChromaVectorStore, JsonVectorStore


def build_embedding_provider(container: ServiceContainer) -> EmbeddingProvider:
    provider = os.getenv("LOCALKIT_EMBEDDING_PROVIDER", "ollama").lower()
    if provider == "deterministic":
        return DeterministicEmbeddingProvider()
    return OllamaEmbeddingProvider(
        base_url=container.settings.ollama_base_url,
        model=container.settings.ollama_embed_model,
    )


def build_vector_store(container: ServiceContainer):
    backend = container.settings.vector_backend.lower()
    if backend == "json":
        return JsonVectorStore(container.settings.data_dir / "vectors.json")
    return ChromaVectorStore(container.settings.chroma_dir)
