from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_data_dir() -> Path:
    configured = os.getenv("LOCALKIT_DATA_DIR")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()
    return (Path.home() / ".localkit-docs").resolve()


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    ollama_base_url: str
    ollama_embed_model: str
    vector_backend: str

    @property
    def database_path(self) -> Path:
        return self.data_dir / "localkit.sqlite3"

    @property
    def sources_dir(self) -> Path:
        return self.data_dir / "sources"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"


def get_settings() -> Settings:
    return Settings(
        data_dir=resolve_data_dir(),
        ollama_base_url=os.getenv("LOCALKIT_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_embed_model=os.getenv("LOCALKIT_OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        vector_backend=os.getenv("LOCALKIT_VECTOR_BACKEND", "chroma"),
    )
