from cli.app import _clip_text, _document_payload, _first_chunk_source_url


class Document:
    id = "doc-1"
    source_id = "source-1"
    path = "guides/vercel.md"
    title = "Vercel"
    chunk_count = 4


def test_document_payload_can_clip_around_query_terms() -> None:
    text = (
        "Drizzle database intro text. " * 80
        + "Use attachDatabasePool with Drizzle ORM."
        + " Outro text." * 80
    )

    payload = _document_payload(Document(), text, 220, query="attachDatabasePool Drizzle ORM")

    assert payload["text"].startswith("... ")
    assert "attachDatabasePool" in payload["text"]
    assert not payload["text"].startswith("... Drizzle intro")
    assert len(payload["text"]) < 260


def test_clip_text_without_query_starts_at_beginning() -> None:
    text = "Intro text. " * 80 + "Use attachDatabasePool with Drizzle ORM."

    clipped = _clip_text(text, 120)

    assert clipped.startswith("Intro text.")
    assert "attachDatabasePool" not in clipped


def test_first_chunk_source_url_reads_chunk_metadata() -> None:
    chunks = [{"metadata": {"source_url": "https://example.com/docs/page"}}]

    assert _first_chunk_source_url(chunks) == "https://example.com/docs/page"
