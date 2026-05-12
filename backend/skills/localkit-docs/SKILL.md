---
name: localkit-docs
description: Use when an agent needs local, CLI-first documentation search through this repository's LocalKit Docs backend. Trigger for finding indexed docs, adding local docs folders, crawling remote docs URLs, refreshing indexes, or retrieving context without using MCP.
---

# LocalKit Docs

Use the `localkit` CLI from `backend/`.

## Workflow

1. Check indexed sources:

```powershell
localkit list
```

2. Add local documentation when the user gives a folder:

```powershell
localkit add-local PATH --name NAME
```

3. Crawl remote documentation when the user gives a URL:

```powershell
localkit add-remote URL --include /docs/ --max-depth 3 --max-pages 100
```

4. Search before answering library or framework questions:

```powershell
localkit search "specific question" --limit 8
```

5. Prefer exact snippets from search results over memory. Include source path names when reporting findings.

## Notes

- This project does not expose an MCP server.
- Ollama must be running for the default embedding provider.
- Data lives under `backend/.localkit-docs/`.
- Set `LOCALKIT_EMBEDDING_PROVIDER=deterministic` and `LOCALKIT_VECTOR_BACKEND=json` only for offline smoke checks.
