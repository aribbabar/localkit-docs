from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


def canonical_url_from_origin_path(origin: str, path: str) -> str | None:
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    clean_path = _clean_document_path(path)
    if not clean_path:
        return origin

    origin_segments = [segment for segment in parsed.path.split("/") if segment]
    path_segments = [segment for segment in clean_path.split("/") if segment]
    docs_root_markers = {"docs", "doc", "documentation", "guide", "guides", "learn"}

    if path_segments and (
        path_segments[0] in docs_root_markers
        or (origin_segments and path_segments[0] == origin_segments[0])
    ):
        return urlunparse((parsed.scheme, parsed.netloc, "/" + "/".join(path_segments), "", "", ""))

    base_path = parsed.path
    if not base_path.endswith("/"):
        base_path = base_path.rsplit("/", 1)[0] + "/"
    return urljoin(urlunparse((parsed.scheme, parsed.netloc, base_path, "", "", "")), clean_path)


def _clean_document_path(path: str) -> str:
    clean_path = path.strip().replace("\\", "/").lstrip("/")
    clean_path = re.sub(r"\.(mdx?|html?)$", "", clean_path)
    clean_path = re.sub(r"/index$", "", clean_path)
    return clean_path
