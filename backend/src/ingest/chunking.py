from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    ordinal: int
    text: str


def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 200) -> list[TextChunk]:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        return []

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
            chunks.append(TextChunk(ordinal=ordinal, text=chunk))
            ordinal += 1
        if end >= len(normalized):
            break
        start = max(0, end - overlap)
    return chunks
