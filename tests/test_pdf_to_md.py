"""Role B conversion checks, using temporary PDFs rather than committed papers."""
from pathlib import Path

import pytest

from paper_lib.pdf_to_md import pdf_to_markdown

pymupdf = pytest.importorskip("pymupdf")
pymupdf4llm = pytest.importorskip("pymupdf4llm")

ABSTRACT = (
    "This research paper studies reliable data pipelines and metadata extraction. "
    "We evaluate reproducible workflows using text-based documents and compare "
    "the resulting summaries with the original abstract. The evaluation discusses "
    "conversion errors, structured metadata, and practical limitations."
)


def make_pdf(path: Path, text: str = ABSTRACT, **save_options) -> Path:
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 540, 750), text, fontsize=11)
        document.save(str(path), **save_options)
    return path


def test_converts_real_pdf_to_utf8_markdown_and_returns_stem_path(tmp_path):
    source = make_pdf(tmp_path / "research.v1.PDF", "Research at the café\n\n" + ABSTRACT)
    original = source.read_bytes()

    result = pdf_to_markdown(source, tmp_path / "nested" / "markdown")

    assert result == tmp_path / "nested" / "markdown" / "research.v1.md"
    markdown = result.read_text(encoding="utf-8")
    assert "café" in markdown
    assert "reliable data pipelines" in markdown
    assert "structured metadata" in markdown
    assert source.read_bytes() == original
    assert list(result.parent.iterdir()) == [result]


def test_two_columns_table_and_simple_formula_survive_conversion(tmp_path):
    source = tmp_path / "layout.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), "A Study of Research Workflows", fontsize=18)
        left = "LEFT COLUMN\n" + ABSTRACT + "\nEnd of the left column."
        right = "RIGHT COLUMN\n" + ABSTRACT + "\nEnd of the right column."
        assert page.insert_textbox(pymupdf.Rect(50, 90, 280, 700), left, fontsize=10) >= 0
        assert page.insert_textbox(pymupdf.Rect(315, 90, 545, 700), right, fontsize=10) >= 0

        page = document.new_page()
        page.insert_text((50, 50), "Experimental Results", fontsize=16)
        page.insert_text((50, 100), "Simple formula: x^2 + y^2 = z^2", fontsize=11)
        for x in (50, 220, 390):
            page.draw_line((x, 150), (x, 240))
        for y in (150, 180, 210, 240):
            page.draw_line((50, y), (390, y))
        for row, values in enumerate((("Model", "Score"), ("Baseline", "0.72"), ("Improved", "0.91"))):
            for column, value in enumerate(values):
                page.insert_text((60 + 170 * column, 170 + 30 * row), value, fontsize=11)
        document.save(str(source))

    markdown = pdf_to_markdown(source, tmp_path / "markdown").read_text(encoding="utf-8")

    assert "A Study of Research Workflows" in markdown
    assert markdown.index("LEFT COLUMN") < markdown.index("End of the left column.")
    assert markdown.index("End of the left column.") < markdown.index("RIGHT COLUMN")
    assert "x^2 + y^2 = z^2" in markdown
    for value in ("Model", "Score", "Baseline", "0.72", "Improved", "0.91"):
        assert value in markdown


def test_missing_file_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="PDF does not exist"):
        pdf_to_markdown(tmp_path / "missing.pdf", tmp_path / "markdown")


def test_directory_is_not_a_pdf_file(tmp_path):
    with pytest.raises(IsADirectoryError, match="not a file"):
        pdf_to_markdown(tmp_path, tmp_path / "markdown")


def test_pdf_with_markdown_suffix_cannot_overwrite_its_source(tmp_path):
    source = make_pdf(tmp_path / "paper.md")
    original = source.read_bytes()

    with pytest.raises(ValueError, match="overwrite source PDF"):
        pdf_to_markdown(source, source.parent)

    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("contents", [b"", b"%PDF-1.7\nnot a valid PDF", b"plain text"])
def test_invalid_pdf_has_clear_error_without_output(tmp_path, contents):
    source = tmp_path / "broken.pdf"
    source.write_bytes(contents)

    with pytest.raises(ValueError, match="Cannot read PDF.*broken.pdf"):
        pdf_to_markdown(source, tmp_path / "markdown")

    assert not (tmp_path / "markdown").exists()


def test_password_protected_pdf_requires_unlocked_copy(tmp_path):
    source = make_pdf(
        tmp_path / "locked.pdf",
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="test-owner",
        user_pw="test-reader",
    )

    with pytest.raises(ValueError, match="password-protected"):
        pdf_to_markdown(source, tmp_path / "markdown")

    assert not (tmp_path / "markdown").exists()


@pytest.mark.parametrize("text", ["", "Page 1", "Only a short title and nothing else."])
def test_nearly_empty_pdf_explains_ocr_limit(tmp_path, text):
    source = make_pdf(tmp_path / "short.pdf", text)

    with pytest.raises(ValueError, match="almost no extractable text.*OCR is not enabled"):
        pdf_to_markdown(source, tmp_path / "markdown")

    assert not (tmp_path / "markdown").exists()


def test_image_only_scanned_pdf_is_rejected_before_conversion(tmp_path, monkeypatch):
    original = make_pdf(tmp_path / "original.pdf")
    with pymupdf.open(str(original)) as document:
        image = document[0].get_pixmap().tobytes("png")
    scanned = tmp_path / "scan.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_image(page.rect, stream=image)
        document.save(str(scanned))

    def unexpected_conversion(*args, **kwargs):
        pytest.fail("An image-only PDF must be rejected before conversion/OCR")

    monkeypatch.setattr(pymupdf4llm, "to_markdown", unexpected_conversion)
    with pytest.raises(ValueError, match="scanned or image-only"):
        pdf_to_markdown(scanned, tmp_path / "markdown")


def test_empty_converter_output_does_not_replace_existing_markdown(tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "paper.pdf")
    out_dir = tmp_path / "markdown"
    out_dir.mkdir()
    existing = out_dir / "paper.md"
    existing.write_text("Previous successful conversion", encoding="utf-8")
    monkeypatch.setattr(pymupdf4llm, "to_markdown", lambda *args, **kwargs: "\n---\n")

    with pytest.raises(ValueError, match="almost no extractable text"):
        pdf_to_markdown(source, out_dir)

    assert existing.read_text(encoding="utf-8") == "Previous successful conversion"
    assert list(out_dir.iterdir()) == [existing]


def test_conversion_failure_names_the_pdf(tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "paper.pdf")

    def fail_conversion(*args, **kwargs):
        assert kwargs["use_ocr"] is False
        assert kwargs["write_images"] is False
        assert kwargs["embed_images"] is False
        raise RuntimeError("malformed page")

    monkeypatch.setattr(pymupdf4llm, "to_markdown", fail_conversion)
    with pytest.raises(ValueError, match="Cannot convert PDF.*paper.pdf.*malformed page"):
        pdf_to_markdown(source, tmp_path / "markdown")


def test_failed_atomic_replace_keeps_previous_markdown_and_removes_temp_file(tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "paper.pdf")
    out_dir = tmp_path / "markdown"
    out_dir.mkdir()
    existing = out_dir / "paper.md"
    existing.write_text("Previous successful conversion", encoding="utf-8")
    monkeypatch.setattr(pymupdf4llm, "to_markdown", lambda *args, **kwargs: ABSTRACT)

    def fail_replace(self, target):
        raise PermissionError("Output file is locked")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(PermissionError, match="locked"):
        pdf_to_markdown(source, out_dir)

    assert existing.read_text(encoding="utf-8") == "Previous successful conversion"
    assert list(out_dir.iterdir()) == [existing]
