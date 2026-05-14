---
name: localkit-docs-search
description: Use when an agent needs to query indexed documentation in this repository's LocalKit Docs backend through the localkit CLI. Trigger before answering framework, library, API, or project documentation questions when relevant docs may be indexed locally.
---

# LocalKit Docs Search

Run from `backend/`.

## Search

Search one docs source by name or id:

```powershell
localkit search "DOCS_NAME" "question or exact term" --limit 8
```

Examples:

```powershell
localkit search "next-js-docs" "how do I configure middleware"
localkit search "react-docs" "useEffect cleanup"
```

## Use Results

- Prefer returned snippets and paths over memory.
- Include source paths when reporting answers.
- A docs name or id is required. If unknown, run `localkit list`.
