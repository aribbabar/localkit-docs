---
name: localkit-docs-search
description: Use when an agent needs to query indexed documentation in this repository's LocalKit Docs backend through the localkit CLI. Trigger before answering framework, library, API, or project documentation questions when relevant docs may be indexed locally.
---

# LocalKit Docs Search

Run from `backend/`. The CLI searches one indexed source at a time.

## Workflow

1. List indexed docs before searching unless the user already provided a source
   name or id:

```powershell
localkit list --output json
```

Use the displayed source name or id exactly. Prefer short names like `neon`,
`react-docs`, or `next-js-docs` when available.

## Search

Search one docs source by name or id:

```powershell
localkit search "DOCS_NAME" "question or exact term" --limit 8 --output json
```

Examples:

```powershell
localkit list --output json
localkit search "next-js-docs" "how do I configure middleware"
localkit search "react-docs" "useEffect cleanup"
localkit search "neon" "Drizzle ORM Neon serverless driver Pool WebSocket constructor" --limit 5 --output json --chars 2400
```

## Show A Full Document

If a search result points to the right document but more context is needed, show
the document by id, exact path, or unique path suffix:

```powershell
localkit show "DOCS_NAME" "docs/serverless/serverless-driver/index.md" --output json
localkit show "neon" "serverless-driver/index.md" --output json
```

## Use Results

- Prefer returned snippets and paths over memory.
- Include source paths when reporting answers.
- A docs name or id is required. If unknown, run `localkit list` first.
- Prefer `--output json` for coding agents so paths, scores, and snippets are
  easy to parse. Use `--chars 2400` or `--chars 0` when code examples or
  endpoint bodies are likely to be longer than the default snippet.
- If the top result has the right path but the snippet is clipped before the
  implementation detail, rerun with a narrower query using exact API names,
  class names, endpoint paths, or option names from the first result, or run
  `localkit show` for the referenced path.
- For coding work, search for the specific task and concrete symbols together:
  framework or package name, method/endpoint, option names, runtime, and error
  text if relevant.
- Do not treat a high-level page hit as sufficient when code, flags, endpoint
  bodies, or lifecycle rules are needed. Refine the query until the snippet
  contains the actionable detail or inspect the referenced local source file.
