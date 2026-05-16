---
name: localkit-docs-add
description: Use when an agent needs to add, crawl, index, refresh, list, or remove documentation sources through the localkit CLI. Trigger for adding local docs folders, adding remote docs URLs, reindexing docs, checking indexed sources, or managing docs sources.
---

# LocalKit Docs Add

Prefer the installed `localkit` command and run it from any working directory.
By default, it uses the shared user-level index at `~/.localkit-docs`, which is
the same index used by the local frontend/backend unless `LOCALKIT_DATA_DIR` is
overridden.

If `localkit` is not on `PATH` and this LocalKit Docs source checkout is
available, run the same commands from `backend/` with `uv run localkit ...`.

## Commands

```powershell
localkit list
localkit add-local PATH --name DOCS_NAME
localkit add-remote URL --name DOCS_NAME --include /docs/ --max-depth 3 --max-pages 1000
localkit index SOURCE_ID
localkit remove SOURCE_ID
```

Use short, stable `DOCS_NAME` values because querying can target them later:

```powershell
localkit add-remote https://nextjs.org/docs --name next-js-docs --include /docs/
```

## Notes

- Ollama should be running for default embeddings.
- Prefer `LOCALKIT_OLLAMA_EMBED_MODEL=nomic-embed-text`, which matches the backend default.
- Do not set `LOCALKIT_DATA_DIR` unless the user explicitly keeps the index in a custom location.
- Reindex after changing embedding model or search behavior.
