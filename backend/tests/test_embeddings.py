from __future__ import annotations

import asyncio

import httpx
import pytest

from storage import embeddings
from storage.embeddings import OllamaEmbeddingProvider


def test_ollama_embeddings_use_current_batch_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    responses = [
        _response(
            "http://127.0.0.1:11434/api/embed",
            200,
            {"embeddings": [[1, "2"], [3, 4]]},
        )
    ]

    _install_fake_async_client(monkeypatch, responses, calls)

    provider = OllamaEmbeddingProvider("http://127.0.0.1:11434", "nomic-embed-text")

    result = asyncio.run(provider.embed(["hello\nworld", "second"]))

    assert result == [[1.0, 2.0], [3.0, 4.0]]
    assert calls == [
        {
            "url": "http://127.0.0.1:11434/api/embed",
            "json": {"model": "nomic-embed-text", "input": ["hello world", "second"]},
        }
    ]


def _install_fake_async_client(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[httpx.Response],
    calls: list[dict[str, object]],
) -> None:
    class FakeAsyncClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, object]) -> httpx.Response:
            calls.append({"url": url, "json": json})
            return responses.pop(0)

    monkeypatch.setattr(embeddings.httpx, "AsyncClient", FakeAsyncClient)


def _response(url: str, status_code: int, payload: dict[str, object]) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        request=httpx.Request("POST", url),
    )
