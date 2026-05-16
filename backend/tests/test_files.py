from __future__ import annotations

from pathlib import Path

import pytest

from ingest import files
from ingest.files import copy_local_source, iter_indexable_files


def test_iter_indexable_files_prunes_ignored_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_walk(root: Path):
        dirnames = ["docs", "node_modules", ".git"]
        yield str(root), dirnames, []
        for dirname in dirnames:
            yield str(root / dirname), [], ["guide.md"]

    monkeypatch.setattr(files.os, "walk", fake_walk)

    paths = [path.relative_to(tmp_path).as_posix() for path in iter_indexable_files(tmp_path)]

    assert paths == ["docs/guide.md"]


def test_copy_local_source_only_copies_indexable_docs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "stored"
    (source / "docs").mkdir(parents=True)
    (source / "docs" / "guide.md").write_text("# Guide", encoding="utf-8")
    (source / "docs" / "image.png").write_bytes(b"png")
    (source / "node_modules" / "pkg").mkdir(parents=True)
    (source / "node_modules" / "pkg" / "readme.md").write_text("ignored", encoding="utf-8")

    copy_local_source(source, destination)

    assert (destination / "docs" / "guide.md").exists()
    assert not (destination / "docs" / "image.png").exists()
    assert not (destination / "node_modules").exists()
