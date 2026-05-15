from __future__ import annotations

import re
from pathlib import Path


def extract_source_url(text: str) -> str | None:
    match = re.search(r"(?im)^\s*source_url:\s*(\S+)\s*$", text)
    return match.group(1).strip() if match else None


def clean_document_text(text: str) -> str:
    text = _strip_leading_metadata_comment(text)
    lines = [_normalize_line(line) for line in text.splitlines()]
    lines = _drop_boilerplate_lines(lines)
    return _collapse_blank_lines(lines).strip()


def infer_document_title(text: str, fallback: str) -> str:
    cleaned = clean_document_text(text)
    fallback_title = _title_from_path(fallback)
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading:
            title = _clean_heading(heading.group(1))
            if title:
                return title
        if _looks_like_content_title(stripped):
            return stripped[:120]
    return fallback_title or fallback


def _strip_leading_metadata_comment(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "<!--":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "-->":
                return "\n".join(lines[index + 1 :])
    return text


def _normalize_line(line: str) -> str:
    stripped = line.rstrip()
    stripped = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", stripped)
    stripped = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", stripped)
    stripped = re.sub(r"\[\]\([^)]+\)", "", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped


def _drop_boilerplate_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            cleaned.append(line)
            continue
        if in_code_block:
            cleaned.append(line)
            continue
        if _is_boilerplate_line(stripped):
            continue
        cleaned.append(line)
    return cleaned


def _is_boilerplate_line(line: str) -> bool:
    if not line:
        return False
    lowered = line.lower()
    exact = {
        "ask ai",
        "copy page",
        "resources",
        "search...",
        "search...⌘k",
        "thank you for your feedback!",
        "was this page helpful?",
        "yesno",
    }
    if lowered in exact:
        return True
    prefixes = (
        "ccpa",
        "gdpr",
        "iso 27001",
        "iso 27701",
        "soc 2",
        "trust center",
    )
    if lowered.startswith(prefixes):
        return True
    if re.fullmatch(r"[-*]\s*(connect|develop|manage|postgres|resources|legal|community|compliance)", lowered):
        return True
    if "all rights reserved" in lowered:
        return True
    if "team accounts with unlimited members" in lowered:
        return True
    return False


def _collapse_blank_lines(lines: list[str]) -> str:
    collapsed: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        collapsed.append("" if blank else line)
        previous_blank = blank
    return "\n".join(collapsed)


def _clean_heading(value: str) -> str:
    value = re.sub(r"\[\]\([^)]+\)", "", value)
    value = re.sub(r"\s+", " ", value.strip().strip("#")).strip()
    return value


def _looks_like_content_title(value: str) -> bool:
    if len(value) > 140:
        return False
    lowered = value.lower()
    if lowered.startswith(("* ", "- ", "//", "source_url:", "status_code:", "saved_at:", "depth:")):
        return False
    return bool(re.search(r"[a-zA-Z]{3,}", value))


def _title_from_path(path: str) -> str:
    stem = Path(path.replace("\\", "/")).stem
    if stem in {"index", "readme"}:
        parent = Path(path.replace("\\", "/")).parent.name
        stem = parent or stem
    return re.sub(r"[-_]+", " ", stem).strip().title()
