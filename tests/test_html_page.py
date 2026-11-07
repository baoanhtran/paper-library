#Static HTML page listing the papers, with search and category filter.

import json
import re

from paper_lib.html_page import build_html

FAKE = [
    {"filename": "a.pdf", "title": "Graph Databases", "summary": "About graphs.",
     "keywords": ["graph", "neo4j"], "category": "Databases"},
    {"filename": "b.pdf", "title": "Tricky </script><b>title</b> & \u2028 more", "summary": "S",
     "keywords": ["k"], "category": "Machine Learning"},
]


def _embedded(html: str):
    m = re.search(r'<script id="papers-data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def test_writes_selfcontained_page(tmp_path):
    out = tmp_path / "output" / "index.html"
    build_html(FAKE, out)
    html = out.read_text(encoding="utf-8")
    assert 'id="q"' in html and 'id="cat"' in html           # search box + category filter
    assert "<style>" in html and "<script>" in html           # inline CSS and JS
    assert "http://" not in html and "https://" not in html   # no external resources


def test_data_roundtrips_and_cannot_break_out_of_script(tmp_path):
    out = tmp_path / "index.html"
    build_html(FAKE, out)
    html = out.read_text(encoding="utf-8")
    assert _embedded(html) == FAKE
    assert html.count("</script>") == 2                       # only our two real closing tags


def test_empty_list(tmp_path):
    out = tmp_path / "index.html"
    build_html([], out)
    assert _embedded(out.read_text(encoding="utf-8")) == []


def test_atomic_write_overwrites_and_leaves_no_temp_files(tmp_path):
    out = tmp_path / "index.html"
    build_html(FAKE, out)
    build_html(FAKE[:1], out)
    assert len(_embedded(out.read_text(encoding="utf-8"))) == 1
    assert [p.name for p in tmp_path.iterdir()] == ["index.html"]


def test_failed_write_keeps_old_page(tmp_path):
    out = tmp_path / "index.html"
    build_html(FAKE, out)
    before = out.read_text(encoding="utf-8")
    bad = [{"filename": "x", "title": object()}]              # not JSON serialisable
    try:
        build_html(bad, out)
    except TypeError:
        pass
    assert out.read_text(encoding="utf-8") == before
    assert [p.name for p in tmp_path.iterdir()] == ["index.html"]
