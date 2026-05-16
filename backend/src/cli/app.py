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
from core.urls import canonical_url_from_origin_path

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
    scope: Annotated[
        str,
        typer.Option("--scope", help="Crawl scope: path or domain. Domain mode can crawl an entire host."),
    ] = "path",
    delay: Annotated[float, typer.Option("--delay", help="Delay between page requests in seconds.")] = 0.15,
    index: Annotated[bool, typer.Option(help="Index immediately after crawling.")] = True,
) -> None:
    scope = _validate_crawl_scope(scope)
    container, source_service, indexer, _, _ = _services()
    progress = _progress_echo()
    source = asyncio.run(
        source_service.add_remote(
            url=url,
            name=name,
            include=include,
            exclude=exclude,
            crawl_scope=scope,
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
    path: Annotated[
        str | None,
        typer.Option("--path", help="Restrict results to paths containing this value or matching this glob."),
    ] = None,
    best_docs: Annotated[
        bool,
        typer.Option("--best-docs", help="Return at most one result per document for broad discovery queries."),
    ] = False,
    require_match: Annotated[
        bool,
        typer.Option("--require-match", help="Only return results whose text, title, path, or section matches a query term."),
    ] = False,
) -> None:
    output = _validate_output(output)
    container, _, _, search_service, _ = _services()
    source = container.sources.resolve(docs)
    if not source:
        raise typer.BadParameter(f"Docs source not found by name or id: {docs}")
    resolved_source_id = source.id
    search_query = query
    requested_limit = min(max(limit * 4, limit), 40) if best_docs or require_match else limit
    results = asyncio.run(
        search_service.search(
            search_query,
            limit=requested_limit,
            source_id=resolved_source_id,
            path_filter=path,
        )
    )
    if require_match:
        results = [result for result in results if _matched_terms(search_query, result)]
    if best_docs:
        results = _best_document_results(results, limit, search_query)
    else:
        results = results[:limit]
    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "source": _source_payload(source, container.documents.source_stats(source.id)),
                    "query": search_query,
                    "path_filter": path,
                    "best_docs": best_docs,
                    "require_match": require_match,
                    "results": [
                        _search_result_payload(result, chars, query=search_query, rank=index)
                        for index, result in enumerate(results, start=1)
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    for index, result in enumerate(results, start=1):
        typer.echo(f"\n{index}. {result.title or result.path}  score={result.score:.3f}")
        typer.echo(f"   {result.path} ({result.source_id})")
        if result.source_url:
            typer.echo(f"   {result.source_url}")
        typer.echo(indent(_clip_text(result.text, chars, query=search_query), "   "))


@app.command("show")
def show(
    docs: Annotated[str, typer.Argument(help="Docs source name or id.")],
    document: Annotated[str, typer.Argument(help="Document id, exact path, or unique path suffix.")],
    output: Annotated[str, typer.Option("--output", help="Output format: text or json.")] = "text",
    chars: Annotated[int, typer.Option("--chars", help="Maximum document characters. Use 0 for full text.")] = 0,
    query: Annotated[
        str | None,
        typer.Option("--query", help="Center clipped output around the first matching query term."),
    ] = None,
) -> None:
    output = _validate_output(output)
    container, _, _, _, _ = _services()
    source = container.sources.resolve(docs)
    if not source:
        raise typer.BadParameter(f"Docs source not found by name or id: {docs}")

    record = container.documents.resolve_document(source.id, document)
    if not record:
        raise typer.BadParameter(f"Document not found by id or path in {source.name}: {document}")

    chunks = container.documents.list_chunks_by_document(record.id)
    text = container.documents.get_document_text(record.id)
    source_url = (
        _first_chunk_source_url(chunks)
        or _extract_source_url(text)
        or canonical_url_from_origin_path(source.origin, record.path)
    )
    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "source": _source_payload(source, container.documents.source_stats(source.id)),
                    "document": _document_payload(record, text, chars, query=query, source_url=source_url),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    typer.echo(f"{record.title or record.path}")
    typer.echo(f"{record.path} ({record.id})")
    if source_url:
        typer.echo(source_url)
    typer.echo("")
    typer.echo(_clip_text(text, chars, query=query))


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


def _validate_crawl_scope(scope: str) -> str:
    normalized = scope.strip().lower()
    if normalized not in {"path", "domain"}:
        raise typer.BadParameter("Crawl scope must be 'path' or 'domain'.")
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
        (len(term), lowered.find(term))
        for term in _query_terms(query)
        if len(term) > 1 and lowered.find(term) >= 0
    ]
    if not matches:
        return None
    _, index = max(matches, key=lambda match: (match[0], -match[1]))
    return index


def _query_terms(query: str) -> list[str]:
    return [
        term
        for term in re.findall(r"[a-z0-9_/@{}.-]{2,}", query.lower())
        if term not in {"and", "for", "how", "the", "with", "what", "when", "where"}
    ]


def _best_document_results(results, limit: int, query: str):
    ranked_results = sorted(
        results,
        key=lambda result: (len(_matched_terms(query, result)), result.score),
        reverse=True,
    )
    selected = []
    seen_document_ids: set[str] = set()
    for result in ranked_results:
        key = result.document_id or result.chunk_id
        if key in seen_document_ids:
            continue
        selected.append(result)
        seen_document_ids.add(key)
        if len(selected) >= limit:
            break
    return selected


def _matched_terms(query: str, result) -> list[str]:
    terms = _query_terms(query)
    if not terms:
        return []
    haystack = "\n".join(
        [
            str(result.title or ""),
            str(result.path or ""),
            str(result.text or ""),
            " ".join(result.section_path or []),
        ]
    ).lower()
    return [term for term in terms if _term_matches(term, haystack)]


def _term_matches(term: str, haystack: str) -> bool:
    if re.fullmatch(r"[a-z0-9_]+", term):
        pattern = rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])"
        return re.search(pattern, haystack) is not None
    return term in haystack


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
        "created_at": _isoformat(getattr(source, "created_at", None)),
        "updated_at": _isoformat(getattr(source, "updated_at", None)),
    }


def _search_result_payload(result, chars: int, *, query: str | None = None, rank: int | None = None) -> dict[str, object]:
    return {
        "rank": rank,
        "chunk_id": result.chunk_id,
        "document_id": result.document_id,
        "score": result.score,
        "source_id": result.source_id,
        "path": result.path,
        "source_url": result.source_url,
        "title": result.title,
        "section_path": result.section_path or [],
        "matched_terms": _matched_terms(query or "", result),
        "text": _clip_text(result.text, chars, query=query),
    }


def _document_payload(
    document,
    text: str,
    chars: int,
    *,
    query: str | None = None,
    source_url: str | None = None,
) -> dict[str, object]:
    return {
        "id": document.id,
        "source_id": document.source_id,
        "path": document.path,
        "source_url": source_url,
        "title": document.title,
        "chunk_count": document.chunk_count,
        "text": _clip_text(text, chars, query=query),
    }


def _extract_source_url(text: str) -> str | None:
    match = re.search(r"(?im)^\s*source_url:\s*(\S+)\s*$", text)
    return match.group(1).strip() if match else None


def _first_chunk_source_url(chunks: list[dict[str, object]]) -> str | None:
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        source_url = metadata.get("source_url")
        if isinstance(source_url, str) and source_url.strip():
            return source_url.strip()
    return None


def _isoformat(value: object) -> str | None:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return None


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
