from ingest.chunking import chunk_text


def test_chunk_text_returns_ordered_chunks() -> None:
    chunks = chunk_text("Alpha. " * 500, chunk_size=120, overlap=20)

    assert chunks
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.text for chunk in chunks)
