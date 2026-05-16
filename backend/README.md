# LocalKit Docs Backend

Python backend and CLI for LocalKit Docs.

## Commands

```powershell
localkit add-local PATH --name NAME
localkit add-remote URL --include /docs/ --include /guide/ --max-depth 3 --max-pages 1000
localkit list
localkit index SOURCE_ID
localkit search DOCS_NAME "query"
localkit show DOCS_NAME DOCUMENT
localkit remove SOURCE_ID
localkit serve --port 8000
```

## Configuration

Environment variables:

- `LOCALKIT_DATA_DIR`: defaults to `~/.localkit-docs`; relative overrides resolve from the current working directory
- `LOCALKIT_OLLAMA_BASE_URL`: defaults to `http://127.0.0.1:11434`
- `LOCALKIT_OLLAMA_EMBED_MODEL`: defaults to `nomic-embed-text`
- `LOCALKIT_VECTOR_BACKEND`: defaults to `chroma`; set `json` for a lightweight dev fallback

## Architecture

- CLI and API share the same service layer.
- SQLite owns source, document, chunk, and job metadata.
- Chroma owns vector persistence and similarity search.
- Ollama owns embedding generation.
- Local and remote ingestion both normalize into files under `.localkit-docs/sources/`, then pass through the same chunking and indexing pipeline.
