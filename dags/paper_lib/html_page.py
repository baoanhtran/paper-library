"""Static HTML page listing the papers, with search and category filter. Owner: C.

STUB: writes a placeholder page so the DAG can run end to end. C replaces the body
with the real page (search box, category filter, atomic write) and keeps the signature.
"""
from __future__ import annotations

from pathlib import Path


def build_html(papers: list[dict], output_path: Path) -> None:
    """Rewrite the whole page at output_path from the given paper records."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"<!DOCTYPE html>\n<title>Research Library</title>\n<p>Stub page: {len(papers)} papers.</p>\n",
        encoding="utf-8",
    )
