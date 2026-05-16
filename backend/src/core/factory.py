from __future__ import annotations

from core.services import ServiceContainer
from storage.embeddings import EmbeddingProvider, OllamaEmbeddingProvider
from storage.vector_store import ChromaVectorStore, JsonVectorStore


def build_embedding_provider(container: ServiceContainer) -> EmbeddingProvider:
    return OllamaEmbeddingProvider(
        base_url=container.settings.ollama_base_url,
        model=container.settings.ollama_embed_model,
    )


def build_vector_store(container: ServiceContainer):
    backend = container.settings.vector_backend.lower()
    if backend == "json":
        return JsonVectorStore(container.settings.data_dir / "vectors.json")
    return ChromaVectorStore(container.settings.chroma_dir)
