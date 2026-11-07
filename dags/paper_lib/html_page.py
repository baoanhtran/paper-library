"""Static HTML page listing the papers, with search and category filter. Owner: C.

The page is one self-contained file: inline CSS and JS, paper data embedded as JSON.
It needs no server and no network, so it works when opened straight from disk
(file://) and when synced through Google Drive.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research Library</title>
<style>
:root{--bg:#fafafa;--fg:#1d1d1f;--muted:#666;--card:#fff;--line:#ddd;--accent:#2f5bea;--chip:#e9eefc}
@media (prefers-color-scheme:dark){
 :root{--bg:#161618;--fg:#ececec;--muted:#9a9a9f;--card:#202023;--line:#38383c;--accent:#7b9bff;--chip:#2a3250}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:900px;margin:0 auto;padding:2rem 1rem 4rem}
h1{margin:0 0 .25rem}
.controls{display:flex;gap:.5rem;flex-wrap:wrap;margin:1rem 0 .5rem}
input,select{font:inherit;padding:.55rem .7rem;border:1px solid var(--line);border-radius:8px;
 background:var(--card);color:var(--fg)}
input{flex:1 1 260px}
.count{color:var(--muted);font-size:.9rem;margin:.25rem 0 1rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1rem 1.1rem;margin-bottom:.8rem}
.card h2{font-size:1.1rem;margin:0 0 .2rem}
.meta{color:var(--muted);font-size:.85rem;word-break:break-all}
.card p{margin:.6rem 0}
.chip{display:inline-block;border:0;background:var(--chip);color:var(--fg);border-radius:999px;
 padding:.1rem .6rem;margin:.15rem .25rem .15rem 0;font:inherit;font-size:.8rem;cursor:pointer}
.chip:hover{outline:1px solid var(--accent)}
.empty{color:var(--muted);text-align:center;padding:2rem}
</style>
</head>
<body>
<main>
<h1>Research Library</h1>
<div class="controls">
 <input id="q" type="search" placeholder="Search title, summary, keywords, filename…" aria-label="Search papers" autofocus>
 <select id="cat" aria-label="Filter by category"><option value="">All categories</option></select>
</div>
<div id="count" class="count"></div>
<div id="list"></div>
</main>
<script id="papers-data" type="application/json">__DATA__</script>
<script>
(function () {
  var papers = JSON.parse(document.getElementById("papers-data").textContent);
  var q = document.getElementById("q"), cat = document.getElementById("cat");
  var list = document.getElementById("list"), count = document.getElementById("count");

  var cats = [];
  papers.forEach(function (p) { if (cats.indexOf(p.category) < 0) cats.push(p.category); });
  cats.sort(function (a, b) { return a.localeCompare(b); }).forEach(function (c) {
    var o = document.createElement("option"); o.value = c; o.textContent = c; cat.appendChild(o);
  });

  function el(tag, text, cls) {
    var e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;   // textContent: never interpret paper text as HTML
    if (cls) e.className = cls;
    return e;
  }

  function render() {
    var terms = q.value.toLowerCase().split(/\\s+/).filter(Boolean);
    var hits = papers.filter(function (p) {
      if (cat.value && p.category !== cat.value) return false;
      var hay = [p.title, p.summary, p.filename, p.category, p.keywords.join(" ")].join(" ").toLowerCase();
      return terms.every(function (t) { return hay.indexOf(t) >= 0; });
    });
    list.replaceChildren();
    hits.forEach(function (p) {
      var card = el("div", undefined, "card");
      card.appendChild(el("h2", p.title));
      card.appendChild(el("div", p.category + " \\u00b7 " + p.filename, "meta"));
      card.appendChild(el("p", p.summary));
      p.keywords.forEach(function (k) {
        var chip = el("button", k, "chip");
        chip.type = "button";
        chip.onclick = function () { q.value = k; render(); };
        card.appendChild(chip);
      });
      list.appendChild(card);
    });
    if (!hits.length) list.appendChild(el("div", papers.length ? "No paper matches." : "No papers yet.", "empty"));
    count.textContent = hits.length + " of " + papers.length + " papers";
  }

  q.addEventListener("input", render);
  cat.addEventListener("change", render);
  render();
})();
</script>
</body>
</html>
"""


def _embed_json(papers: list[dict]) -> str:
    """JSON that is safe inside a <script> element."""
    text = json.dumps(papers, ensure_ascii=False)
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def build_html(papers: list[dict], output_path: Path) -> None:
    """Rewrite the whole page at output_path from the given paper records."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = _TEMPLATE.replace("__DATA__", _embed_json(papers))

    # Atomic write: write a temp file in the same folder, then rename over the target.
    # Google Drive therefore never uploads a half-written index.html.
    fd, tmp_name = tempfile.mkstemp(dir=output_path.parent, prefix=".index-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(html)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, output_path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
