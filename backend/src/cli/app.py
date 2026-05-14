from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

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
    include: Annotated[str | None, typer.Option("--include", help="Only crawl URLs containing this value.")] = None,
    exclude: Annotated[str | None, typer.Option("--exclude", help="Skip URLs containing this value.")] = None,
    max_depth: Annotated[int, typer.Option("--max-depth")] = 3,
    max_pages: Annotated[int, typer.Option("--max-pages")] = 100,
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
) -> None:
    container, _, _, search_service, _ = _services()
    source = container.sources.resolve(docs)
    if not source:
        raise typer.BadParameter(f"Docs source not found by name or id: {docs}")
    resolved_source_id = source.id
    search_query = query
    results = asyncio.run(search_service.search(search_query, limit=limit, source_id=resolved_source_id))
    for index, result in enumerate(results, start=1):
        typer.echo(f"\n{index}. {result.title or result.path}  score={result.score:.3f}")
        typer.echo(f"   {result.path} ({result.source_id})")
        typer.echo(indent(result.text[:700].replace("\n", " "), "   "))


@app.command("list")
def list_sources() -> None:
    container, _, _, _, _ = _services()
    for source in container.sources.list():
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
