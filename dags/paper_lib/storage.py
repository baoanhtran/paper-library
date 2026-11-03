"""SQLite storage for paper records. Owner: C.

STUB: returns fake data so the DAG can run end to end. C replaces the bodies with
sqlite3 code for the papers table in the contract and keeps the signatures.
"""
from __future__ import annotations

from pathlib import Path


def init_db(db_path: Path) -> None:
    """Create the papers table if it does not exist."""


def get_processed_filenames(db_path: Path) -> set[str]:
    """Return the filenames already stored in the papers table."""
    return set()


def save_paper(db_path: Path, filename: str, metadata: dict) -> None:
    """Insert the paper, or update it if the filename is already stored."""


def get_paper(db_path: Path, filename: str) -> dict | None:
    """Return the paper record for filename, or None if it is not stored."""
    return {
        "filename": filename,
        "title": "Stub title",
        "summary": "Stub summary.",
        "keywords": ["stub"],
        "category": "Other",
    }


def get_all_papers(db_path: Path) -> list[dict]:
    """Return every paper record, with keywords decoded back to list[str]."""
    return []
