"""PDF to Markdown conversion. Owner: B.

STUB: writes fake Markdown so the DAG can run end to end. B replaces the body
with the pymupdf4llm conversion and keeps the signature from the contract.
"""
from __future__ import annotations

from pathlib import Path


def pdf_to_markdown(pdf_path: Path, out_dir: Path) -> Path:
    """Convert one PDF with pymupdf4llm, write <stem>.md into out_dir, return its path."""
    pdf_path, out_dir = Path(pdf_path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{pdf_path.stem}.md"
    md_path.write_text(f"# {pdf_path.stem}\n\nStub Markdown for {pdf_path.name}.\n", encoding="utf-8")
    return md_path
