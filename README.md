# LocalKit Docs

LocalKit Docs is a local-first documentation index for coding agents.

It lets you add local folders or remote documentation sites, index them with local embeddings, and search them from a CLI. Agents can use the included skills to search indexed docs before answering framework, library, API, or project-specific questions.

The backend is a Python CLI/API. The frontend is an optional local UI.

## Requirements

- `uv` for the Python CLI and backend
- Node.js and npm for the optional frontend
- Ollama running locally for the default embedding provider

Install `uv`:

```powershell
winget install astral-sh.uv
```

On macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Ollama and pull the default embedding model:

```bash
ollama pull nomic-embed-text
```

## Install The CLI

Install from the remote Git repo:

```bash
uv tool install "git+https://github.com/OWNER/localkit-docs.git#subdirectory=backend"
```

Replace `OWNER` with the GitHub owner for this repo. This checkout does not currently have a Git remote configured, so the README cannot name the final URL yet.

Check that it works:

```bash
localkit list
```

## Use The CLI

Add local documentation:

```bash
localkit add-local ./docs --name my-docs
```

Add remote documentation:

```bash
localkit add-remote https://example.com/docs --name example-docs --include /docs/ --max-depth 3 --max-pages 1000
```

List indexed sources:

```bash
localkit list
```

Search one source by name or id:

```bash
localkit search my-docs "how do I configure authentication?"
```

Show a full document from a source:

```bash
localkit show my-docs path/to/page.md
```

## Updates

If you installed the CLI with `uv tool install` from Git, update it with:

```bash
uv tool upgrade localkit-docs
```

For maintainers, the simplest release flow is:

1. Push changes to the default branch.
2. Bump `backend/pyproject.toml` when the CLI behavior changes.
3. Create a GitHub release or tag with the same version.
4. Tell users to run `uv tool upgrade localkit-docs`.

Users who want update notifications can watch GitHub releases for the repo. Avoid adding automatic update checks to the CLI unless the project later needs that extra network behavior.

## Agent Skills

This repo includes ready-made skills under `backend/skills/`:

- `localkit-docs-add` for adding, indexing, listing, and removing sources
- `localkit-docs-search` for searching and showing indexed docs

Copy the folders you want into one of your agent skill directories:

```text
~/.codex/skills/
```

or:

```text
~/.agents/skills/
```

Restart your agent after adding or updating skills.

## Local Development

On Windows, run the backend and frontend together:

```powershell
.\run-dev.ps1
```

Optional ports:

```powershell
.\run-dev.ps1 -BackendPort 8000 -FrontendPort 5173
```

The script runs `uv sync` for the backend and `npm install` for the frontend when needed. Use `-SkipInstall` if dependencies are already installed.

Backend only:

```bash
cd backend
uv sync
uv run localkit serve --port 8000
```

Frontend only:

```bash
cd frontend
npm install
npm run dev
```
