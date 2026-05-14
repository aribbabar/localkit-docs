from pathlib import Path

from storage.database import Database
from storage.repositories import DocumentRepository, SourceRecord, SourceRepository


def test_repositories_persist_sources_documents_and_chunks(tmp_path: Path) -> None:
    database = Database(tmp_path / "localkit.sqlite3")
    try:
        sources = SourceRepository(database)
        documents = DocumentRepository(database)

        source = SourceRecord(
            id="source-1",
            name="Docs",
            kind="local",
            origin="E:/docs",
            stored_path="E:/stored",
            status="pending",
            options={"include": "*.md"},
        )

        sources.upsert(source)
        sources.set_status(source.id, "indexed")
        documents.add_document("document-1", source.id, "index.md", "Index", "hash")
        documents.add_chunk("chunk-1", "document-1", source.id, 0, "Hello docs", {"path": "index.md"})

        stored_source = sources.get(source.id)
        assert stored_source is not None
        assert stored_source.status == "indexed"
        assert stored_source.options == {"include": "*.md"}
        assert sources.resolve("Docs").id == source.id
        assert sources.resolve(source.id).name == "Docs"
        assert documents.source_stats(source.id) == {"documents": 1, "chunks": 1}
        assert documents.list_by_source(source.id)[0].chunk_count == 1
        assert documents.get_chunk("chunk-1")["document_path"] == "index.md"

        documents.replace_source_chunks(source.id)

        assert documents.source_stats(source.id) == {"documents": 0, "chunks": 0}
    finally:
        database.close()
