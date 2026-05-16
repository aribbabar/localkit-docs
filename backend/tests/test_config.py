from pathlib import Path

from core.config import backend_root, resolve_data_dir


def test_backend_root_is_backend_directory() -> None:
    assert backend_root().name == "backend"
    assert (backend_root() / "pyproject.toml").exists()


def test_default_data_dir_is_user_level(monkeypatch) -> None:
    monkeypatch.delenv("LOCALKIT_DATA_DIR", raising=False)

    assert resolve_data_dir() == (Path.home() / ".localkit-docs").resolve()


def test_relative_configured_data_dir_resolves_from_cwd(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALKIT_DATA_DIR", ".localkit-docs")
    monkeypatch.chdir(tmp_path)

    assert resolve_data_dir() == (tmp_path / ".localkit-docs").resolve()


def test_absolute_configured_data_dir_is_respected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALKIT_DATA_DIR", str(tmp_path))

    assert resolve_data_dir() == tmp_path.resolve()
