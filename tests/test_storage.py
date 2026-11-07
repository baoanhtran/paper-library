#SQLite storage for paper records.

import sqlite3

import pytest

from paper_lib import storage

META = {"title": "Paper A", "summary": "About A.", "keywords": ["x", "y"], "category": "Machine Learning"}


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "nested" / "papers.db"
    storage.init_db(path)  # also creates the parent folder
    return path


def test_init_is_idempotent(db):
    storage.init_db(db)
    assert storage.get_all_papers(db) == []


def test_schema_columns(db):
    with sqlite3.connect(db) as conn:
        cols = {r[1]: r[5] for r in conn.execute("PRAGMA table_info(papers)")}
    assert {"filename", "title", "summary", "keywords", "category"} <= set(cols)
    assert cols["filename"] == 1  # primary key


def test_save_and_get_roundtrip(db):
    storage.save_paper(db, "a.pdf", META)
    assert storage.get_paper(db, "a.pdf") == {"filename": "a.pdf", **META}


def test_keywords_stored_as_json_string(db):
    storage.save_paper(db, "a.pdf", META)
    with sqlite3.connect(db) as conn:
        raw = conn.execute("SELECT keywords FROM papers").fetchone()[0]
    assert raw == '["x", "y"]'


def test_unicode_keywords(db):
    storage.save_paper(db, "u.pdf", {**META, "keywords": ["données", "数据"]})
    assert storage.get_paper(db, "u.pdf")["keywords"] == ["données", "数据"]


def test_get_missing_returns_none(db):
    assert storage.get_paper(db, "nope.pdf") is None


def test_save_twice_updates_not_duplicates(db):
    storage.save_paper(db, "a.pdf", META)
    storage.save_paper(db, "a.pdf", {**META, "title": "New title"})
    papers = storage.get_all_papers(db)
    assert len(papers) == 1 and papers[0]["title"] == "New title"


def test_processed_filenames(db):
    assert storage.get_processed_filenames(db) == set()
    storage.save_paper(db, "a.pdf", META)
    storage.save_paper(db, "b.pdf", META)
    assert storage.get_processed_filenames(db) == {"a.pdf", "b.pdf"}


def test_get_all_sorted_by_title(db):
    storage.save_paper(db, "1.pdf", {**META, "title": "zebra"})
    storage.save_paper(db, "2.pdf", {**META, "title": "Apple"})
    assert [p["title"] for p in storage.get_all_papers(db)] == ["Apple", "zebra"]


def test_connection_is_closed(db):
    storage.save_paper(db, "a.pdf", META)
    db.rename(db.with_name("moved.db"))  # a leaked handle would block this on Windows
