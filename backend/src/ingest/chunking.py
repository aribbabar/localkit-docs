from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TextChunk:
    ordinal: int
    text: str
    title: str | None = None
    path: tuple[str, ...] = ()
    types: tuple[str, ...] = ()


def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 200) -> list[TextChunk]:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        return []

    markdown_chunks = _chunk_markdown_sections(normalized, chunk_size=chunk_size, overlap=overlap)
    if markdown_chunks:
        return markdown_chunks

    chunks: list[TextChunk] = []
    start = 0
    ordinal = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = max(normalized.rfind("\n\n", start, end), normalized.rfind(". ", start, end))
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(TextChunk(ordinal=ordinal, text=chunk, types=("text",)))
            ordinal += 1
        if end >= len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def _chunk_markdown_sections(text: str, chunk_size: int, overlap: int) -> list[TextChunk]:
    sections = _markdown_sections(text)
    if not sections:
        return []

    chunks: list[TextChunk] = []
    ordinal = 0
    for section in sections:
        for section_part in _split_long_section(section["text"], chunk_size, overlap):
            chunk_text = section_part.strip()
            if not chunk_text:
                continue
            chunks.append(
                TextChunk(
                    ordinal=ordinal,
                    text=chunk_text,
                    title=section["title"],
                    path=tuple(section["path"]),
                    types=("markdown",),
                )
            )
            ordinal += 1
    return chunks


def _markdown_sections(text: str) -> list[dict[str, object]]:
    body = _strip_front_matter(text)
    lines = body.splitlines()
    sections: list[dict[str, object]] = []
    heading_stack: list[tuple[int, str]] = []
    current_lines: list[str] = []
    current_title: str | None = None
    current_path: list[str] = []

    def flush() -> None:
        nonlocal current_lines, current_title, current_path
        content = "\n".join(current_lines).strip()
        if content:
            sections.append(
                {
                    "title": current_title,
                    "path": list(current_path),
                    "text": content,
                }
            )
        current_lines = []

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            flush()
            level = len(match.group(1))
            title = _clean_heading(match.group(2))
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            current_title = title
            current_path = [heading for _, heading in heading_stack]
            current_lines = [line]
            continue

        if current_lines or line.strip():
            current_lines.append(line)

    flush()

    if len(sections) == 1 and not sections[0]["path"]:
        return []
    return sections


def _strip_front_matter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return "\n".join(lines[index + 1 :]).strip()
    if lines and lines[0].strip() == "<!--":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "-->":
                return "\n".join(lines[index + 1 :]).strip()
    return text


def _clean_heading(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("#")).strip()


def _split_long_section(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks
