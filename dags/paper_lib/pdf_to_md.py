"""Convert text-based research PDFs to Markdown. Owner: B."""
from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

# Count letters and digits, rather than Markdown separators or image references.
# A title or a page number alone is not enough input for a useful paper summary.
MIN_TEXT_CHARACTERS = 100


def _text_characters(text: str) -> int:
    return sum(character.isalnum() for character in text)


def _require_text(text_characters: int, pdf_path: Path) -> None:
    if text_characters < MIN_TEXT_CHARACTERS:
        raise ValueError(
            f"PDF '{pdf_path}' contains almost no extractable text "
            f"({text_characters} letters/digits; at least {MIN_TEXT_CHARACTERS} required). "
            "It may be scanned or image-only; OCR is not enabled. "
            "Provide a text-based PDF or run OCR before adding it to the library."
        )


def pdf_to_markdown(pdf_path: Path, out_dir: Path) -> Path:
    """Convert a text-based PDF, atomically write <stem>.md, and return its path.

    OCR and image export are disabled. Invalid, password-protected, or nearly
    textless documents raise ValueError without replacing an existing Markdown
    file. File access and output write errors propagate to the caller.
    """
    pdf_path, out_dir = Path(pdf_path), Path(out_dir)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF does not exist: {pdf_path}")
    if not pdf_path.is_file():
        raise IsADirectoryError(f"PDF path is not a file: {pdf_path}")
    md_path = out_dir / f"{pdf_path.stem}.md"
    if md_path.resolve() == pdf_path.resolve():
        raise ValueError(f"Markdown output would overwrite source PDF: {pdf_path}")

    # Airflow can import this helper without loading the PDF engine.
    import pymupdf
    import pymupdf4llm

    try:
        document = pymupdf.open(str(pdf_path))
    except (pymupdf.FileDataError, pymupdf.EmptyFileError) as exc:
        raise ValueError(f"Cannot read PDF '{pdf_path}': {exc}") from exc

    with document:
        if not document.is_pdf:
            raise ValueError(f"Input is not a PDF document: {pdf_path}")
        if document.needs_pass:
            raise ValueError(f"PDF '{pdf_path}' is password-protected; provide an unlocked copy.")

        # Check native text before conversion: image captions and Markdown image
        # paths must not make an otherwise scanned document appear usable.
        _require_text(sum(_text_characters(page.get_text()) for page in document), pdf_path)
        try:
            markdown = pymupdf4llm.to_markdown(
                document,
                use_ocr=False,
                write_images=False,
                embed_images=False,
                page_chunks=False,
                show_progress=False,
            )
        except (RuntimeError, ValueError) as exc:
            raise ValueError(f"Cannot convert PDF '{pdf_path}' to Markdown: {exc}") from exc

    _require_text(_text_characters(markdown), pdf_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=out_dir, prefix=f".{pdf_path.stem}.", suffix=".tmp", delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(markdown.rstrip() + "\n")
        temporary_path.replace(md_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return md_path
