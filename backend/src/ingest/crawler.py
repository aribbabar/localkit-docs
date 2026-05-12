from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown

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


@dataclass(frozen=True)
class CrawlResult:
    project_dir: Path
    pages_dir: Path
    saved_pages: int


def infer_remote_name(start_url: str) -> str:
    parsed = urlparse(start_url)
    host = parsed.hostname or "remote-docs"
    path_parts = [part for part in parsed.path.split("/") if part]
    if path_parts and path_parts[0].lower() in {"docs", "documentation", "guide", "guides"}:
        return slugify(f"{host}-{path_parts[0]}", "remote-docs")
    return slugify(host.replace("www.", ""), "remote-docs")


async def crawl_remote(
    start_url: str,
    output_dir: Path,
    options: CrawlOptions,
    progress: ProgressCallback | None = None,
) -> CrawlResult:
    normalized_start = normalize_url(start_url)
    origin = url_origin(normalized_start)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    queue: deque[tuple[str, int]] = deque([(normalized_start, 0)])
    seen: set[str] = set()
    records: list[dict[str, object]] = []
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

    async with httpx.AsyncClient(follow_redirects=True, timeout=options.timeout_seconds) as client:
        while queue and len(records) < options.max_pages:
            url, depth = queue.popleft()
            if url in seen or depth > options.max_depth:
                continue
            seen.add(url)

            if not url.startswith(origin) or not matches_filters(url, options):
                continue

            try:
                if progress:
                    progress(
                        {
                            "phase": "crawl",
                            "status": "running",
                            "message": "Fetching page",
                            "current": len(records),
                            "total": options.max_pages,
                            "current_item": url,
                        }
                    )
                response = await client.get(url, headers={"User-Agent": "localkit-docs/0.1"})
                content_type = response.headers.get("content-type", "")
                if response.status_code >= 400 or "text/html" not in content_type:
                    records.append(page_record(url, depth, None, False, response.status_code))
                    if progress:
                        progress(
                            {
                                "phase": "crawl",
                                "status": "running",
                                "message": "Skipped page",
                                "current": len(records),
                                "total": options.max_pages,
                                "current_item": url,
                            }
                        )
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                title = (soup.title.string.strip() if soup.title and soup.title.string else url)
                markdown = html_to_markdown(str(soup), heading_style="ATX").strip()
                target_path = pages_dir / path_for_url(url)
                write_page(target_path, url, title, markdown)
                records.append(page_record(url, depth, target_path, True, response.status_code))

                for href in extract_links(soup, url):
                    next_url = normalize_url(href)
                    if next_url not in seen and next_url.startswith(origin):
                        queue.append((next_url, depth + 1))
            except Exception as exc:  # noqa: BLE001 - record crawler failures and continue.
                records.append(page_record(url, depth, None, False, None, str(exc)))
                if progress:
                    progress(
                        {
                            "phase": "crawl",
                            "status": "running",
                            "message": "Page failed",
                            "current": len(records),
                            "total": options.max_pages,
                            "current_item": url,
                        }
                    )

            if progress:
                progress(
                    {
                        "phase": "crawl",
                        "status": "running",
                        "message": "Processed page",
                        "current": len(records),
                        "total": options.max_pages,
                        "current_item": url,
                    }
                )

            if options.delay_seconds > 0:
                await asyncio.sleep(options.delay_seconds)

    manifest = {
        "start_url": normalized_start,
        "saved_pages": sum(1 for record in records if record["success"]),
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "options": options.__dict__,
        "pages": records,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if progress:
        progress(
            {
                "phase": "crawl",
                "status": "running",
                "message": f"Saved {manifest['saved_pages']} pages",
                "current": len(records),
                "total": options.max_pages,
            }
        )
    return CrawlResult(
        project_dir=output_dir,
        pages_dir=pages_dir,
        saved_pages=int(manifest["saved_pages"]),
    )


def normalize_url(raw_url: str) -> str:
    raw_url = raw_url.strip()
    if "://" not in raw_url:
        raw_url = f"https://{raw_url}"
    parsed = urlparse(raw_url)
    clean, _ = urldefrag(parsed.geturl())
    parsed = urlparse(clean)
    path = parsed.path or "/"
    return parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower(), path=path).geturl()


def url_origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def matches_filters(url: str, options: CrawlOptions) -> bool:
    if options.include and options.include not in url:
        return False
    if options.exclude and options.exclude in url:
        return False
    return True


def extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links: list[str] = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href")
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        links.append(urljoin(base_url, href))
    return links


def path_for_url(url: str) -> Path:
    parsed = urlparse(url)
    parts = [slugify(part, "page") for part in parsed.path.split("/") if part]
    if not parts:
        return Path("index.md")
    if "." in parts[-1]:
        parts[-1] = parts[-1].rsplit(".", 1)[0]
    return Path(*parts).with_suffix(".md")


def write_page(path: Path, source_url: str, title: str, markdown: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"---\nsource_url: {source_url}\ntitle: {title}\n---\n\n{markdown}\n"
    path.write_text(content, encoding="utf-8")


def page_record(
    url: str,
    depth: int,
    saved_path: Path | None,
    success: bool,
    status_code: int | None,
    error: str | None = None,
) -> dict[str, object]:
    return {
        "url": url,
        "depth": depth,
        "saved_path": str(saved_path) if saved_path else None,
        "success": success,
        "status_code": status_code,
        "error": error,
    }
