from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

from core.progress import ProgressCallback

SUPPORTED_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mdx",
    ".py",
    ".rst",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".localkit-docs",
    ".next",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
}


def copy_local_source(
    source_path: Path,
    destination: Path,
    overwrite: bool = True,
    progress: ProgressCallback | None = None,
) -> Path:
    source_path = source_path.expanduser().resolve()
    if not source_path.exists() or not source_path.is_dir():
        raise ValueError(f"Local source directory does not exist: {source_path}")
    if destination.exists() and overwrite:
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = list(_iter_copyable_files(source_path))
    if progress:
        progress(
            {
                "phase": "copy",
                "status": "running",
                "message": "Copying local docs",
                "current": 0,
                "total": len(files),
            }
        )
    destination.mkdir(parents=True, exist_ok=True)
    for index, file_path in enumerate(files, start=1):
        relative_path = file_path.relative_to(source_path)
        target_path = destination / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target_path)
        if progress:
            progress(
                {
                    "phase": "copy",
                    "status": "running",
                    "message": "Copied local file",
                    "current": index,
                    "total": len(files),
                    "current_item": relative_path.as_posix(),
                }
            )
    return destination


def iter_indexable_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _iter_copyable_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def _ignore_names(_: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_DIRS}
