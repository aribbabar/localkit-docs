# LocalKit Docs

LocalKit Docs is a local-first documentation index for coding agents.

It lets you add local folders or remote documentation sites, index them with local embeddings, and search them from a CLI. Agents can use the included skill to search your indexed docs before answering framework, library, or project-specific questions.

The backend is a Python CLI/API. The frontend is an optional local UI.

## Setup

Install `uv`.

Windows:

```powershell
winget install astral-sh.uv
```

macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Ollama and pull the default embedding model:

```bash
ollama pull nomic-embed-text
```

Install the CLI from this repo:

```bash
uv tool install "git+https://github.com/YOUR_ORG/localkit-docs.git#subdirectory=backend"
```

Check that it works:

```bash
localkit list
```

Add documentation:

```bash
localkit add-local ./docs --name my-docs
```

or:

```bash
localkit add-remote https://example.com/docs --include /docs/ --max-depth 3 --max-pages 100
```

Search:

```bash
localkit search "how do I configure authentication?"
```

## Agent Skill

Create a skill folder:

```text
~/.codex/skills/localkit-docs/
```

or:

```text
~/.agents/skills/localkit-docs/
```

Create `SKILL.md` in that folder:

````markdown
---
name: localkit-docs
description: Use when an agent needs local CLI-first documentation search through LocalKit Docs.
---

# LocalKit Docs

Use the `localkit` CLI to search indexed documentation before answering library, framework, or project-doc questions.

Check indexed sources:

```bash
localkit list
```

Add local documentation:

```bash
localkit add-local PATH --name NAME
```

Add remote documentation:

```bash
localkit add-remote URL --include /docs/ --max-depth 3 --max-pages 100
```

Search docs:

```bash
localkit search "specific question" --limit 8
```

Prefer search results over memory, and mention source paths when useful.
````

Restart your agent after adding the skill.

## Local Development

Run the backend and frontend together:

```powershell
.\run-dev.ps1
```

Optional ports:

```powershell
.\run-dev.ps1 -BackendPort 8000 -FrontendPort 5173
```

Backend:

```bash
cd backend
uv sync
fastapi dev main.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```
