---
name: localkit-docs-add
description: Use when an agent needs to add, crawl, index, refresh, list, or remove documentation sources in this repository's LocalKit Docs backend through the localkit CLI. Trigger for adding local docs folders, adding remote docs URLs, reindexing docs, checking indexed sources, or managing docs sources.
---

# LocalKit Docs Add

Run from `backend/`.

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
- Prefer `LOCALKIT_OLLAMA_EMBED_MODEL=nomic-embed-text:latest`.
- Reindex after changing embedding model or search behavior.
