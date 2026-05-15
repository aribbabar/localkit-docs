from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint, event, text
from sqlmodel import Field, Session, SQLModel, create_engine


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Source(SQLModel, table=True):
    __tablename__ = "sources"

    id: str = Field(primary_key=True)
    name: str
    kind: str
    origin: str
    stored_path: str
    status: str = "pending"
    options_json: str = "{}"
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Document(SQLModel, table=True):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source_id", "path"),)

    id: str = Field(primary_key=True)
    source_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    path: str
    title: str | None = None
    content_hash: str
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"

    id: str = Field(primary_key=True)
    document_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    source_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    ordinal: int
    text: str
    metadata_json: str = "{}"
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: str = Field(primary_key=True)
    source_id: str | None = Field(
        default=None,
        sa_column=Column(String, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
    )
    kind: str
    status: str
    message: str | None = None
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.path}", connect_args={"check_same_thread": False})
        event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)
        self.initialize()

    @contextmanager
    def session(self) -> Iterator[Session]:
        with Session(self.engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def initialize(self) -> None:
        SQLModel.metadata.create_all(self.engine)
        self._initialize_fts()

    def close(self) -> None:
        self.engine.dispose()

    @staticmethod
    def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def _initialize_fts(self) -> None:
        with self.engine.begin() as connection:
            fts_exists = (
                connection.execute(
                    text(
                        """
                        SELECT 1
                        FROM sqlite_master
                        WHERE type = 'table' AND name = 'chunks_fts'
                        """
                    )
                ).scalar()
                is not None
            )
            connection.execute(
                text(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                        chunk_id UNINDEXED,
                        source_id UNINDEXED,
                        document_id UNINDEXED,
                        content,
                        title,
                        path,
                        tokenize='porter unicode61'
                    )
                    """
                )
            )
            if not fts_exists:
                connection.execute(
                    text(
                        """
                        INSERT INTO chunks_fts(chunk_id, source_id, document_id, content, title, path)
                        SELECT c.id, c.source_id, c.document_id, c.text, COALESCE(d.title, ''), d.path
                        FROM chunks c
                        JOIN documents d ON d.id = c.document_id
                        """
                    )
                )
