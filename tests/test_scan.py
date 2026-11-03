"""New-PDF detection used by the find_new_pdfs task."""
import os
import time

import pytest

from paper_lib.scan import list_new_pdfs


def make_pdf(path, age_seconds=3600):
    path.write_bytes(b"%PDF-1.4\n")
    mtime = time.time() - age_seconds
    os.utime(path, (mtime, mtime))
    return path


def test_returns_unprocessed_pdfs_sorted_by_name(tmp_path):
    for name in ("b.pdf", "a.PDF", "done.pdf"):
        make_pdf(tmp_path / name)
    (tmp_path / "notes.txt").write_text("not a paper")
    (tmp_path / "folder.pdf").mkdir()
    assert [p.name for p in list_new_pdfs(tmp_path, {"done.pdf"})] == ["a.PDF", "b.pdf"]


def test_skips_files_that_may_still_be_syncing(tmp_path):
    make_pdf(tmp_path / "old.pdf", age_seconds=3600)
    make_pdf(tmp_path / "fresh.pdf", age_seconds=1)
    assert [p.name for p in list_new_pdfs(tmp_path, set(), min_age_seconds=30)] == ["old.pdf"]


def test_skips_hidden_files(tmp_path):
    make_pdf(tmp_path / ".partial.pdf")
    assert list_new_pdfs(tmp_path, set()) == []


def test_missing_folder_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="PAPERS_DIR"):
        list_new_pdfs(tmp_path / "missing", set())
