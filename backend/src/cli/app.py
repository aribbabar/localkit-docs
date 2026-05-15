from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Annotated, Optional

import typer

from core.factory import build_embedding_provider, build_vector_store
from core.indexer import Indexer
from core.progress import ProgressCallback, ProgressEvent
from core.search import SearchService
from core.services import build_container
from core.sources import SourceService

app = typer.Typer(help="Local-first semantic docs for agents and humans.", no_args_is_help=True)


def _services():
    container = build_container()
    embeddings = build_embedding_provider(container)
    vector_store = build_vector_store(container)
    source_service = SourceService(container.sources, container.settings.sources_dir)
    indexer = Indexer(container.sources, container.documents, embeddings, vector_store)
    search = SearchService(embeddings, vector_store, container.documents, container.sources)
    return container, source_service, indexer, search, vector_store


@app.command("add-local")
def add_local(
    path: Annotated[Path, typer.Argument(help="Local docs folder to copy into LocalKit.")],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    index: Annotated[bool, typer.Option(help="Index immediately after copying.")] = True,
) -> None:
    container, source_service, indexer, _, _ = _services()
    progress = _progress_echo()
    source = source_service.add_local(path, name, progress=progress)
    typer.echo(f"Added local source {source.name} ({source.id})")
    if index:
        stats = asyncio.run(indexer.index_source(source, progress=progress))
        typer.echo(f"Indexed {stats['documents']} documents into {stats['chunks']} chunks")
    typer.echo(f"Data: {container.settings.data_dir}")


@app.command("add-remote")
def add_remote(
    url: Annotated[str, typer.Argument(help="Remote docs URL to crawl.")],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    include: Annotated[
        Optional[list[str]],
        typer.Option("--include", help="Only crawl URLs matching this pattern. Can be passed multiple times."),
    ] = None,
    exclude: Annotated[
        Optional[list[str]],
        typer.Option("--exclude", help="Skip URLs matching this pattern. Can be passed multiple times."),
    ] = None,
    max_depth: Annotated[int, typer.Option("--max-depth")] = 3,
    max_pages: Annotated[int, typer.Option("--max-pages")] = 1000,
    delay: Annotated[float, typer.Option("--delay", help="Delay between page requests in seconds.")] = 0.15,
    index: Annotated[bool, typer.Option(help="Index immediately after crawling.")] = True,
) -> None:
    container, source_service, indexer, _, _ = _services()
    progress = _progress_echo()
    source = asyncio.run(
        source_service.add_remote(
            url=url,
            name=name,
            include=include,
            exclude=exclude,
            max_depth=max_depth,
            max_pages=max_pages,
            delay_seconds=delay,
            progress=progress,
        )
    )
    typer.echo(f"Added remote source {source.name} ({source.id})")
    if index:
        stats = asyncio.run(indexer.index_source(source, progress=progress))
        typer.echo(f"Indexed {stats['documents']} documents into {stats['chunks']} chunks")
    typer.echo(f"Data: {container.settings.data_dir}")


@app.command("index")
def index_source(source_id: Annotated[str, typer.Argument(help="Source id to index.")]) -> None:
    container, _, indexer, _, _ = _services()
    source = container.sources.get(source_id)
    if not source:
        raise typer.BadParameter(f"Source not found: {source_id}")
    stats = asyncio.run(indexer.index_source(source, progress=_progress_echo()))
    typer.echo(f"Indexed {stats['documents']} documents into {stats['chunks']} chunks")


@app.command("search")
def search(
    docs: Annotated[str, typer.Argument(help="Docs source name or id to search.")],
    query: Annotated[str, typer.Argument(help="Natural language search query.")],
    limit: Annotated[int, typer.Option("--limit", "-l")] = 8,
    output: Annotated[str, typer.Option("--output", help="Output format: text or json.")] = "text",
    chars: Annotated[int, typer.Option("--chars", help="Maximum snippet characters per result. Use 0 for full text.")] = 1200,
) -> None:
    output = _validate_output(output)
    container, _, _, search_service, _ = _services()
    source = container.sources.resolve(docs)
    if not source:
        raise typer.BadParameter(f"Docs source not found by name or id: {docs}")
    resolved_source_id = source.id
    search_query = query
    results = asyncio.run(search_service.search(search_query, limit=limit, source_id=resolved_source_id))
    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "source": _source_payload(source, container.documents.source_stats(source.id)),
                    "query": search_query,
                    "results": [_search_result_payload(result, chars, query=search_query) for result in results],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    for index, result in enumerate(results, start=1):
        typer.echo(f"\n{index}. {result.title or result.path}  score={result.score:.3f}")
        typer.echo(f"   {result.path} ({result.source_id})")
        typer.echo(indent(_clip_text(result.text, chars, query=search_query), "   "))


@app.command("show")
def show(
    docs: Annotated[str, typer.Argument(help="Docs source name or id.")],
    document: Annotated[str, typer.Argument(help="Document id, exact path, or unique path suffix.")],
    output: Annotated[str, typer.Option("--output", help="Output format: text or json.")] = "text",
    chars: Annotated[int, typer.Option("--chars", help="Maximum document characters. Use 0 for full text.")] = 0,
) -> None:
    output = _validate_output(output)
    container, _, _, _, _ = _services()
    source = container.sources.resolve(docs)
    if not source:
        raise typer.BadParameter(f"Docs source not found by name or id: {docs}")

    record = container.documents.resolve_document(source.id, document)
    if not record:
        raise typer.BadParameter(f"Document not found by id or path in {source.name}: {document}")

    text = container.documents.get_document_text(record.id)
    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "source": _source_payload(source, container.documents.source_stats(source.id)),
                    "document": _document_payload(record, text, chars),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    typer.echo(f"{record.title or record.path}")
    typer.echo(f"{record.path} ({record.id})")
    typer.echo("")
    typer.echo(_clip_text(text, chars))


@app.command("list")
def list_sources(
    output: Annotated[str, typer.Option("--output", help="Output format: text or json.")] = "text",
) -> None:
    output = _validate_output(output)
    container, _, _, _, _ = _services()
    sources = container.sources.list()
    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "sources": [
                        _source_payload(source, container.documents.source_stats(source.id))
                        for source in sources
                    ]
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    for source in sources:
        stats = container.documents.source_stats(source.id)
        typer.echo(
            f"{source.id}  {source.kind:<6}  {source.status:<8}  "
            f"{stats['documents']} docs  {stats['chunks']} chunks  {source.name}"
        )


@app.command("remove")
def remove_source(source_id: Annotated[str, typer.Argument(help="Source id to remove.")]) -> None:
    _, source_service, _, _, vector_store = _services()
    removed = source_service.remove(source_id)
    vector_store.delete_source(source_id)
    typer.echo("Removed" if removed else "Source not found")


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p")] = 8000,
) -> None:
    import uvicorn

    uvicorn.run("api.app:app", host=host, port=port, reload=False)


def indent(value: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" for line in value.splitlines())


def _validate_output(output: str) -> str:
    normalized = output.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be 'text' or 'json'.")
    return normalized


def _clip_text(text: str, chars: int, *, query: str | None = None) -> str:
    if chars <= 0 or len(text) <= chars:
        return text
    if not query:
        return f"{text[:chars].rstrip()}..."

    match_start = _first_query_match(text, query)
    if match_start is None or match_start <= chars // 3:
        return f"{text[:chars].rstrip()}..."

    context_before = max(120, chars // 3)
    start = max(0, match_start - context_before)
    start = _move_to_boundary(text, start)
    end = min(len(text), start + chars)
    prefix = "... " if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def _first_query_match(text: str, query: str) -> int | None:
    lowered = text.lower()
    matches = [
        lowered.find(term)
        for term in _query_terms(query)
        if len(term) > 1 and lowered.find(term) >= 0
    ]
    return min(matches) if matches else None


def _query_terms(query: str) -> list[str]:
    return [
        term.lower()
        for term in re.findall(r"[a-z0-9_/@{}.-]{2,}", query)
        if term.lower() not in {"and", "for", "how", "the", "with", "what", "when", "where"}
    ]


def _move_to_boundary(text: str, index: int) -> int:
    newline = text.rfind("\n", 0, index)
    if newline >= max(0, index - 160):
        return newline + 1
    space = text.rfind(" ", 0, index)
    if space >= max(0, index - 80):
        return space + 1
    return index


def _source_payload(source, stats: dict[str, int]) -> dict[str, object]:
    return {
        "id": source.id,
        "name": source.name,
        "kind": source.kind,
        "status": source.status,
        "origin": source.origin,
        "documents": stats["documents"],
        "chunks": stats["chunks"],
    }


def _search_result_payload(result, chars: int, *, query: str | None = None) -> dict[str, object]:
    return {
        "chunk_id": result.chunk_id,
        "document_id": result.document_id,
        "score": result.score,
        "source_id": result.source_id,
        "path": result.path,
        "title": result.title,
        "text": _clip_text(result.text, chars, query=query),
    }


def _document_payload(document, text: str, chars: int) -> dict[str, object]:
    return {
        "id": document.id,
        "source_id": document.source_id,
        "path": document.path,
        "title": document.title,
        "chunk_count": document.chunk_count,
        "text": _clip_text(text, chars),
    }


def _progress_echo() -> ProgressCallback:
    last_line = ""

    def echo(event: ProgressEvent) -> None:
        nonlocal last_line
        item = event.get("current_item")
        if not item:
            return
        phase = event.get("phase", "work")
        current = event.get("current")
        total = event.get("total")
        counter = f"{current}/{total}" if current is not None and total else str(current or "")
        line = f"{phase}: {counter} {item}".strip()
        if line == last_line:
            return
        last_line = line
        typer.echo(line)

    return echo
