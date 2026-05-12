from __future__ import annotations

from dataclasses import dataclass

from core.config import Settings, get_settings
from storage.database import Database
from storage.repositories import DocumentRepository, SourceRepository


@dataclass
class ServiceContainer:
    settings: Settings
    database: Database
    sources: SourceRepository
    documents: DocumentRepository


def build_container() -> ServiceContainer:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    database = Database(settings.database_path)
    return ServiceContainer(
        settings=settings,
        database=database,
        sources=SourceRepository(database),
        documents=DocumentRepository(database),
    )
