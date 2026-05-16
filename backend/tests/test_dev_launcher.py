from pathlib import Path


def test_windows_dev_launcher_uses_subprocess_capable_backend_server() -> None:
    script = Path(__file__).resolve().parents[2] / "run-dev.ps1"

    content = script.read_text(encoding="utf-8")

    assert "run fastapi run main.py" in content
    assert "run fastapi dev main.py" not in content
