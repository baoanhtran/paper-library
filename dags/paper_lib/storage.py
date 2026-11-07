"""SQLite storage for paper records. Owner: C.

One row per paper, keyed by filename (filenames are assumed unique). Keywords are stored
as a JSON string and decoded back to list[str] on the way out. The database lives on the
local machine, never in the Google Drive folder.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    filename     TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    summary      TEXT NOT NULL,
    keywords     TEXT NOT NULL,          -- JSON array of strings
    category     TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_COLUMNS = "filename, title, summary, keywords, category"


@contextmanager
def _connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success, roll back on error, always close.

    The timeout matters: mapped Airflow tasks can write at the same time.
    """
    conn = sqlite3.connect(Path(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        with conn:  # commit / rollback
            yield conn
    finally:
        conn.close()


def _row_to_record(row: sqlite3.Row) -> dict:
    return {
        "filename": row["filename"],
        "title": row["title"],
        "summary": row["summary"],
        "keywords": json.loads(row["keywords"]),
        "category": row["category"],
    }


def init_db(db_path: Path) -> None:
    """Create the papers table if it does not exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")  # readers do not block the writer
        conn.execute(SCHEMA)


def get_processed_filenames(db_path: Path) -> set[str]:
    """Return the filenames already stored in the papers table."""
    with _connect(db_path) as conn:
        return {row["filename"] for row in conn.execute("SELECT filename FROM papers")}


def save_paper(db_path: Path, filename: str, metadata: dict) -> None:
    """Insert the paper, or update it if the filename is already stored."""
    with _connect(db_path) as conn:
        conn.execute(
            f"""INSERT INTO papers ({_COLUMNS}) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(filename) DO UPDATE SET
                    title = excluded.title,
                    summary = excluded.summary,
                    keywords = excluded.keywords,
                    category = excluded.category,
                    processed_at = CURRENT_TIMESTAMP""",
            (
                filename,
                metadata["title"],
                metadata["summary"],
                json.dumps(list(metadata["keywords"]), ensure_ascii=False),
                metadata["category"],
            ),
        )


def get_paper(db_path: Path, filename: str) -> dict | None:
    """Return the paper record for filename, or None if it is not stored."""
    with _connect(db_path) as conn:
        row = conn.execute(
            f"SELECT {_COLUMNS} FROM papers WHERE filename = ?", (filename,)
        ).fetchone()
    return _row_to_record(row) if row else None


def get_all_papers(db_path: Path) -> list[dict]:
    """Return every paper record, with keywords decoded back to list[str]."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM papers ORDER BY title COLLATE NOCASE, filename"
        ).fetchall()
    return [_row_to_record(row) for row in rows]
