"""Every module must keep the signatures from the interface contract (ROADMAP.md, section 6)."""
import inspect

import pytest

from paper_lib import html_page, llm_metadata, notify, pdf_to_md, storage

CONTRACT = [
    (pdf_to_md.pdf_to_markdown, ["pdf_path", "out_dir"]),
    (llm_metadata.extract_metadata, ["markdown", "base_url", "model"]),
    (storage.init_db, ["db_path"]),
    (storage.get_processed_filenames, ["db_path"]),
    (storage.save_paper, ["db_path", "filename", "metadata"]),
    (storage.get_paper, ["db_path", "filename"]),
    (storage.get_all_papers, ["db_path"]),
    (html_page.build_html, ["papers", "output_path"]),
    (notify.notify_new_paper, ["webhook_url", "record"]),
]


@pytest.mark.parametrize("func, params", CONTRACT, ids=[func.__name__ for func, _ in CONTRACT])
def test_signature_matches_contract(func, params):
    assert list(inspect.signature(func).parameters) == params


def test_categories_end_with_other():
    assert llm_metadata.CATEGORIES[-1] == "Other"
