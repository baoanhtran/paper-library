"""Find the PDFs that still have to be processed. Owner: A."""
from __future__ import annotations

import time
from pathlib import Path


def list_new_pdfs(
    papers_dir: Path, processed: set[str], min_age_seconds: float = 30, now: float | None = None
) -> list[Path]:
    """Return the PDFs in papers_dir whose filename is not in processed, sorted by name.

    Hidden files and files modified less than min_age_seconds ago are skipped: Google Drive
    may still be writing them, and the next scheduled run picks them up.
    """
    papers_dir = Path(papers_dir)
    if not papers_dir.is_dir():
        raise FileNotFoundError(f"PAPERS_DIR does not exist or is not a folder: {papers_dir}")
    now = time.time() if now is None else now
    new = []
    for path in papers_dir.iterdir():
        if path.name.startswith(".") or path.suffix.lower() != ".pdf" or not path.is_file():
            continue
        if path.name in processed or now - path.stat().st_mtime < min_age_seconds:
            continue
        new.append(path)
    return sorted(new, key=lambda path: path.name)
