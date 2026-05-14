from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlparse, urlunparse

from core.ids import slugify
from core.progress import ProgressCallback


@dataclass(frozen=True)
class CrawlOptions:
    include: str | None = None
    exclude: str | None = None
    max_depth: int = 3
    max_pages: int = 100
    delay_seconds: float = 0.15
    timeout_seconds: float = 20.0
    fresh: bool = False
    show_browser: bool = False
    text_mode: bool = False
    verbose: bool = False


@dataclass(frozen=True)
class CrawlResult:
    project_dir: Path
    pages_dir: Path
    saved_pages: int


@dataclass
class PageOutput:
    relative_path: str
    extension: str
    content: str
    markdown_kind: str


def infer_remote_name(start_url: str) -> str:
    return infer_project_name(normalize_url(start_url))


async def crawl_remote(
    start_url: str,
    output_dir: Path,
    options: CrawlOptions,
    progress: ProgressCallback | None = None,
) -> CrawlResult:
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
        from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
        from crawl4ai.deep_crawling.filters import ContentTypeFilter, DomainFilter, FilterChain, URLPatternFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    except ImportError as exc:
        raise RuntimeError(
            "Crawl4AI is required for remote docs crawling.\n"
            "Install it with:\n"
            "  pip install -U crawl4ai\n"
            "  crawl4ai-setup\n"
            "If Chromium is still missing, run:\n"
            "  python -m playwright install chromium"
        ) from exc

    normalized_start = normalize_url(start_url)
    scope_prefix = resolve_scope_prefix(normalized_start, options.include)
    output_dir = output_dir.resolve()
    pages_dir = output_dir / "pages"
    manifest_path = output_dir / "manifest.json"
    checkpoint_path = output_dir / "checkpoint.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    resume_state = None if options.fresh else load_json(checkpoint_path)
    existing_manifest = load_json(manifest_path) or {}
    page_records = {
        page["url"]: page
        for page in existing_manifest.get("pages", [])
        if isinstance(page, dict) and page.get("url")
    }

    def save_manifest(status: str, pages_crawled: int | None = None) -> None:
        success_count = sum(1 for record in page_records.values() if record.get("success"))
        failure_count = sum(1 for record in page_records.values() if not record.get("success"))
        manifest = {
            "project_name": output_dir.name,
            "start_url": normalized_start,
            "scope_prefix": scope_prefix,
            "output_dir": str(output_dir),
            "pages_dir": str(pages_dir),
            "status": status,
            "started_at": existing_manifest.get("started_at", utc_now_iso()),
            "updated_at": utc_now_iso(),
            "resumed_from_checkpoint": resume_state is not None,
            "max_depth": options.max_depth,
            "max_pages": options.max_pages,
            "pages_crawled": pages_crawled if pages_crawled is not None else len(page_records),
            "success_count": success_count,
            "failure_count": failure_count,
            "pages": sorted(page_records.values(), key=lambda record: record["url"]),
        }
        atomic_write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))

    async def persist_checkpoint(state: dict[str, Any]) -> None:
        atomic_write_text(checkpoint_path, json.dumps(state, indent=2, ensure_ascii=False))
        save_manifest(status="running", pages_crawled=state.get("pages_crawled"))

    parsed_scope = urlparse(scope_prefix)
    allowed_host = parsed_scope.hostname
    if not allowed_host:
        raise ValueError(f"Unable to determine allowed host from scope prefix: {scope_prefix}")

    filter_chain = FilterChain(
        [
            DomainFilter(allowed_domains=[allowed_host]),
            URLPatternFilter(patterns=scope_patterns(scope_prefix)),
            ContentTypeFilter(allowed_types=["text/html"]),
        ]
    )
    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=options.max_depth,
        max_pages=options.max_pages,
        include_external=False,
        filter_chain=filter_chain,
        resume_state=resume_state,
        on_state_change=persist_checkpoint,
    )
    browser_config = BrowserConfig(
        headless=not options.show_browser,
        text_mode=options.text_mode,
        verbose=options.verbose,
    )
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,
        deep_crawl_strategy=deep_crawl_strategy,
        markdown_generator=DefaultMarkdownGenerator(options={"citations": True}),
        scraping_strategy=LXMLWebScrapingStrategy(),
        stream=True,
        verbose=options.verbose,
        exclude_external_links=True,
        exclude_social_media_links=True,
    )

    if progress:
        progress(
            {
                "phase": "crawl",
                "status": "running",
                "message": "Starting remote crawl",
                "current": 0,
                "total": options.max_pages,
                "current_item": normalized_start,
            }
        )
    save_manifest(status="starting")

    async with AsyncWebCrawler(config=browser_config) as crawler:
        stream = await crawler.arun(url=normalized_start, config=run_config)
        async for result in stream:
            if options.exclude and options.exclude in str(getattr(result, "url", "")):
                continue
            page_output = extract_page_output(result)
            relative_path = page_path_for_url(result.url, page_output.extension)
            page_output.relative_path = relative_path.as_posix()
            output_path = pages_dir / relative_path
            atomic_write_text(output_path, build_saved_content(result, page_output))

            metadata = getattr(result, "metadata", {}) or {}
            record = {
                "url": result.url,
                "saved_path": str(output_path),
                "relative_path": page_output.relative_path,
                "success": bool(getattr(result, "success", False)),
                "status_code": getattr(result, "status_code", None),
                "depth": metadata.get("depth"),
                "score": metadata.get("score"),
                "error_message": getattr(result, "error_message", None),
                "markdown_kind": page_output.markdown_kind,
                "updated_at": utc_now_iso(),
            }
            page_records[result.url] = record
            save_manifest(status="running")

            if progress:
                progress(
                    {
                        "phase": "crawl",
                        "status": "running",
                        "message": "Saved page",
                        "current": len(page_records),
                        "total": options.max_pages,
                        "current_item": page_output.relative_path,
                    }
                )

    final_state = deep_crawl_strategy.export_state()
    if final_state:
        atomic_write_text(checkpoint_path, json.dumps(final_state, indent=2, ensure_ascii=False))

    save_manifest(status="completed", pages_crawled=len(page_records))
    saved_pages = sum(1 for record in page_records.values() if record.get("success"))
    if progress:
        progress(
            {
                "phase": "crawl",
                "status": "running",
                "message": f"Saved {saved_pages} pages",
                "current": len(page_records),
                "total": options.max_pages,
            }
        )
    return CrawlResult(project_dir=output_dir, pages_dir=pages_dir, saved_pages=saved_pages)


def normalize_url(raw_url: str) -> str:
    raw_url = raw_url.strip()
    if "://" not in raw_url:
        raw_url = f"https://{raw_url}"

    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {raw_url}")

    normalized_path = parsed.path or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            "",
            parsed.query,
            "",
        )
    )


def resolve_scope_prefix(start_url: str, include: str | None) -> str:
    if not include:
        return infer_scope_prefix(start_url)
    include = include.strip()
    if not include:
        return infer_scope_prefix(start_url)
    if "://" in include:
        return normalize_url(include)
    return normalize_url(urljoin(start_url, include))


def infer_project_name(start_url: str) -> str:
    parsed = urlparse(start_url)
    host = parsed.hostname or "docs-site"
    host_parts = [part for part in host.split(".") if part not in {"www"}]
    if len(host_parts) >= 2 and host_parts[0] in {"docs", "doc", "documentation"}:
        candidate = host_parts[1]
    else:
        candidate = host_parts[0]

    path_parts = [part for part in parsed.path.split("/") if part]
    if candidate in {"readthedocs", "gitbook"} and path_parts:
        candidate = path_parts[0]

    return slugify(candidate, "docs-site")


def infer_scope_prefix(start_url: str) -> str:
    parsed = urlparse(start_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path or "/"

    if path == "/":
        return base

    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return base

    docs_root_markers = {
        "docs",
        "doc",
        "documentation",
        "guide",
        "guides",
        "learn",
        "manual",
        "reference",
    }
    landing_page_markers = {
        "index",
        "home",
        "intro",
        "introduction",
        "overview",
        "start",
        "quickstart",
        "quick-start",
        "getting-started",
        "get-started",
        "welcome",
        "readme",
    }

    first_segment = segments[0].lower()
    last_segment = segments[-1].lower()
    trimmed = path.rstrip("/")

    if first_segment in docs_root_markers:
        scoped_path = "/" + first_segment
    elif "." in last_segment:
        scoped_path = trimmed.rsplit("/", 1)[0] or "/"
    elif last_segment in landing_page_markers and len(segments) > 1:
        scoped_path = "/" + "/".join(segments[:-1])
    else:
        scoped_path = trimmed

    if scoped_path == "/":
        return base
    return f"{base}{scoped_path}"


def scope_patterns(scope_prefix: str) -> list[str]:
    clean_prefix = scope_prefix.rstrip("/")
    return [clean_prefix, f"{clean_prefix}/", f"{clean_prefix}/*"]


def page_path_for_url(url: str, extension: str) -> Path:
    parsed = urlparse(url)
    path = parsed.path or "/"
    segments = [segment for segment in path.split("/") if segment]

    if not segments:
        base_path = Path("index")
    elif path.endswith("/"):
        base_path = Path(*segments) / "index"
    else:
        last_segment = segments[-1]
        if "." in last_segment:
            stem = re.sub(r"\.[^.]+$", "", last_segment)
            base_path = Path(*segments[:-1]) / stem
        else:
            base_path = Path(*segments) / "index"

    if parsed.query:
        query_slug = slugify("&".join(f"{key}-{value}" for key, value in parse_qsl(parsed.query)), "query")
        base_path = base_path.with_name(f"{base_path.name}__q_{query_slug}")

    return base_path.with_suffix(extension)


def extract_page_output(result: Any) -> PageOutput:
    markdown_obj = getattr(result, "markdown", None)

    if isinstance(markdown_obj, str) and markdown_obj.strip():
        return PageOutput("", ".md", markdown_obj, "string_markdown")

    cited_markdown = getattr(markdown_obj, "markdown_with_citations", None)
    references_markdown = getattr(markdown_obj, "references_markdown", None)
    raw_markdown = getattr(markdown_obj, "raw_markdown", None)
    if cited_markdown or raw_markdown:
        content = cited_markdown or raw_markdown
        if references_markdown and references_markdown not in content:
            content = f"{content}\n\n{references_markdown}".strip()
        return PageOutput(
            "",
            ".md",
            content,
            "markdown_with_citations" if cited_markdown else "raw_markdown",
        )

    cleaned_html = getattr(result, "cleaned_html", None)
    if cleaned_html:
        return PageOutput("", ".html", cleaned_html, "cleaned_html_fallback")

    html = getattr(result, "html", "") or ""
    return PageOutput("", ".html", html, "html_fallback")


def build_saved_content(result: Any, page_output: PageOutput) -> str:
    metadata = getattr(result, "metadata", {}) or {}
    header_lines = [
        "<!--",
        f"source_url: {getattr(result, 'url', '')}",
        f"status_code: {getattr(result, 'status_code', '')}",
        f"depth: {metadata.get('depth', '')}",
        f"saved_at: {utc_now_iso()}",
        "-->",
        "",
    ]
    return "\n".join(header_lines) + page_output.content


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
