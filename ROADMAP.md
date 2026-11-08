# Assignment 3 Roadmap: Research Library Pipeline with Airflow

INFO-H420 Process Modeling, Data Pipelines, and Responsible AI (ULB). Assignment 3: Workflows with Airflow, 10 points.

| | |
|---|---|
| **Deliverable** | A short report (PDF) uploaded to UV → "Assignment 3", with a link to a public GitHub repo (code, README, run instructions) |
| **Deadline** | Monday 9 November 2026 (our internal deadlines: §4) |
| **Roles** | **A** Airflow, integration, demo machine · **B** PDF conversion + local LLM · **C** SQLite, HTML page, Discord, report editor |
| **Report** | LaTeX on OpenAI Prism |
| **Last update** | Sun 8 Nov 2026 (ticked boxes in §5 show what is done) |

## 1. What we are building

One scheduled Airflow DAG that turns the PDFs dropped into a Google Drive folder into a searchable static web page.

```text
Google Drive  ResearchLibrary/papers/*.pdf
      │  synced to the demo machine
      ▼
Airflow DAG "paper_pipeline" (every 5 min, demo machine, WSL2)
  1. find PDFs whose filename is not in the database yet
  2. convert each new PDF to Markdown (PyMuPDF4LLM)
  3. ask a local LLM (Ollama, OpenAI-compatible API) for JSON: title, summary, keywords, category
  4. save the metadata in SQLite: data/papers.db (local, NOT in Drive)
  5. regenerate ResearchLibrary/output/index.html (search + category filter)
  6. send one Discord webhook message per new paper
      │  synced back
      ▼
Google Drive  ResearchLibrary/output/index.html
```

## 2. Roles and points

| Grading criterion | Points | Owner | Evidence |
|---|---|---|---|
| Airflow DAG and task dependencies | 3 | A | `paper_pipeline.py`, Graph and Grid screenshots |
| PDF conversion and local LLM integration | 3 | B | `pdf_to_md.py`, `llm_metadata.py`, prompt, example output |
| SQLite storage, static HTML output, Discord notification | 2 | C | `storage.py`, `html_page.py`, `notify.py`, screenshots |
| Project report and documentation | 2 | Everyone writes, C edits | Report PDF, README |

- A owns the repo and runs the demo machine. After joining the repo, B and C claim their roles (B or C) in the group chat.
- Everyone writes the report and README parts about what they built (§9). C has the lighter coding share (2 points vs 3), so C also sets up the report, does the final pass and submits.

## 3. How we work without waiting on each other

- **The interface contract (§6) is final.** Everyone codes against it, so nobody needs anyone else's code to start or to test.
- **Every file has exactly one owner**: code, tests, README section, report section. Only edit your own files. If you need a change in someone else's file, ask them in the group chat.
- **A pushes the complete skeleton before inviting B and C**: folders, `requirements.txt` with every dependency, `.env.example` with every setting, the README headings, and a stub for every function in §6. B and C never need to edit shared files.
- **Everyone tests with their own data**: B with their own PDFs and a local LLM, C with fake paper records and their own test webhook, A with the stubs until the real modules are merged.
- **Only A needs Airflow and the demo machine.** B and C write and test plain Python on their own laptops.
- **Merge your own PRs** once your tests pass. Nobody waits for a review; A reads everything while integrating.
- **The only things that cross between people:** B posts the recommended model name in the group chat (until then A uses `qwen2.5:7b`), B and C merge their modules by the code deadline, and everyone writes their report sections by the report deadline (§4).

Rules:

- Post in the group chat when you merge something, and when you are stuck for more than ~2 hours.
- Done means: matches §6, has tests, no hard-coded paths or secrets, merged into `main`.
- Code, comments, commit messages, README and report in English.
- Never commit secrets (webhook URL), the database, PDFs, virtualenvs or Airflow logs.

## 4. Deadlines

These are the only fixed dates. Organise your own work around them.

| When | Who | What |
|---|---|---|
| **Fri 6 Nov, 23:59** | B, C | Modules and tests merged into `main` |
| **Sun 8 Nov, 18:00** | Everyone | Report sections written in Prism, README sections done. A: real-run screenshots uploaded, repo public |
| **Mon 9 Nov, 12:00** | C | Report PDF uploaded to UV |

## 5. Tasks per person

Checklists, not schedules: do them in any order that suits you, as long as §4 holds.

### A: Airflow, integration, demo machine (3 pts)

Owns `dags/paper_pipeline.py`, `dags/paper_lib/config.py`, the shared repo files (`requirements.txt`, `.env.example`, `.gitignore`), the demo machine, the Google Drive folder, the demo Discord webhook, all end-to-end runs, and report sections 2, 3 and 6.

- [x] Create the GitHub repo with the full skeleton (§7): folders, `requirements.txt` with every dependency (B's and C's included), `.gitignore`, `.env.example` with every setting from §6, the README headings (§9) and a stub for every function in §6 that returns fake data.
- [x] Invite B and C to the repo (C has not accepted the invitation yet).
- [x] Check that the group is registered on UV ("Groups for Assignment 3").
- [x] Set up the demo machine (§8):
  - [x] Airflow 3.3.2 standalone in WSL2 (`~/venvs/airflow`, `AIRFLOW_HOME=~/airflow`)
  - [x] Ollama 0.40 as a systemd service; `qwen2.5:7b` runs 100% on the GPU
  - [x] Google Drive for Desktop with `ResearchLibrary/papers/` and `ResearchLibrary/output/`
  - [x] Discord channel with a webhook for the demo
- [x] `config.py`: read every setting from environment variables. Load `.env` with `python-dotenv`, so tasks see the settings no matter which terminal started Airflow.
- [x] The DAG (§6), built and tested on the stubs with `airflow dags test paper_pipeline`: schedule every 5 min, `catchup=False`, `max_active_runs=1`, task retries. Also checked: a run with nothing new skips everything, and a failing paper does not stop the others.
- [x] Choose 6–8 demo PDFs on different topics; keep 2 aside to upload during the test (8 arXiv papers, one per category, in `data/demo-pdfs/` on the demo machine).
- [ ] As B's and C's modules are merged: end-to-end runs and the integration checklist (§10). Report bugs to the owner in the group chat. B's modules merged and checked on 5 Nov; C's on 8 Nov. The full pipeline passed in a test setup (new papers, nothing new, one more paper); the real run on the demo machine is next.
- [ ] Take the screenshots of the real run (§9) and upload them to the Prism project.
- [x] README: Overview and architecture, Setup, Run and test, Troubleshooting (§9).
- [ ] Report sections 2, 3 and 6 (2 and 3 drafted and compiled, to paste into Prism once the project exists; 6 after the real run).
- [ ] Make the repo public before the report deadline.

### B: PDF conversion and local LLM (3 pts)

Owns `dags/paper_lib/pdf_to_md.py`, `dags/paper_lib/llm_metadata.py`, their tests, the README section "LLM setup", and report sections 4 and 7. Works on their own laptop with their own sample PDFs; no Airflow needed.

- [x] Install Ollama (or LM Studio) and get a first JSON answer through the `openai` client.
- [x] `pdf_to_markdown()` (§6): check the output on your sample PDFs (two-column layouts, tables, formulas). Raise a clear error when a PDF gives almost no text (e.g. a scanned paper).
- [x] `extract_metadata()` (§6): the category list in the prompt; only the beginning of the paper as input (e.g. the first ~8,000 characters: title, abstract, introduction); low temperature; JSON mode; `json.loads`; retry once; type checks; light cleanup (trim, de-duplicate keywords, unknown category → `Other`); `ValueError` if the second attempt fails too.
- [x] Unit tests with a fake LLM client: valid JSON / invalid then valid / invalid twice / missing field.
- [x] Compare 2 models you can run (quality and seconds per paper) and post your recommendation in the group chat. The demo machine has 8 GB of VRAM, so a 7–8B model works there too.
- [x] README "LLM setup": installing Ollama, pulling the model, switching to LM Studio.
- [ ] Report sections 4 (with 1–2 example LLM outputs) and 7 (written in `docs/sections/`, to copy into Prism).

### C: SQLite, HTML page, Discord, report editor (2 pts + editing)

Owns `dags/paper_lib/storage.py`, `html_page.py`, `notify.py`, their tests, the README sections "Discord webhook", "Configuration", "Project structure" and "Outputs", the Prism project, report sections 1 and 5, and the submission. Works on their own laptop with fake data; no Airflow needed.

- [x] Create the Prism project with the skeleton in §9 and share it with A and B (Share menu, edit rights).
- [x] `storage.py` (§6): the schema and the five functions; pytest on a temporary DB.
- [x] `html_page.py`: one self-contained `index.html` (inline CSS and JS, data embedded as JSON) with a search box and a category filter. It must work when opened straight from disk. Atomic write (§8). Test with fake records.
- [x] `notify.py`: one message per paper (title, category, keywords, short summary, filename); 10 s timeout; raise on HTTP errors; respect Discord's length limits. Test with your own webhook.
- [x] README: Discord webhook, Configuration (the settings in §6 as a table), Project structure (§7), Outputs (database, web page, message format).
- [x] Report sections 1 and 5, with screenshots of your page and a Discord message from your own tests.
- [ ] After the report deadline: final pass on the report and README for consistency (layout, references, typos; no rewriting of others' content), compile the PDF, run the final checklist (§11), upload to UV.

## 6. Interface contract (final)

Everyone codes against this. Change a signature only after telling the others in the group chat.

### Shared data shape

The metadata dict is exactly the JSON from the assignment:

```json
{
  "title": "Paper title",
  "summary": "A short summary of the paper.",
  "keywords": ["keyword one", "keyword two"],
  "category": "Data Engineering"
}
```

A *paper record* is this dict plus `"filename"` (e.g. `"paper.pdf"`).

### Module functions

```python
# dags/paper_lib/config.py (A): values come from environment variables, see .env.example
PAPERS_DIR: Path            # Drive-synced folder with the PDFs
OUTPUT_HTML: Path           # Drive-synced output/index.html
DB_PATH: Path               # local SQLite file, default data/papers.db
MARKDOWN_DIR: Path          # local folder for the converted .md files, default data/markdown
LLM_BASE_URL: str           # e.g. http://localhost:11434/v1
LLM_MODEL: str              # e.g. qwen2.5:7b
DISCORD_WEBHOOK_URL: str    # secret, never committed

# dags/paper_lib/pdf_to_md.py (B)
def pdf_to_markdown(pdf_path: Path, out_dir: Path) -> Path:
    """Convert one PDF with pymupdf4llm, write <stem>.md into out_dir, return its path."""

# dags/paper_lib/llm_metadata.py (B)
CATEGORIES: list[str]       # fixed category list, last item "Other"
def extract_metadata(markdown: str, base_url: str, model: str) -> dict:
    """Return the metadata dict. JSON mode + json.loads; retry once on bad JSON or
    missing/wrong-type fields; raise ValueError if the second attempt fails too."""

# dags/paper_lib/storage.py (C)
def init_db(db_path: Path) -> None: ...                                   # CREATE TABLE IF NOT EXISTS
def get_processed_filenames(db_path: Path) -> set[str]: ...
def save_paper(db_path: Path, filename: str, metadata: dict) -> None: ...  # insert or update by filename
def get_paper(db_path: Path, filename: str) -> dict | None: ...           # paper record, or None
def get_all_papers(db_path: Path) -> list[dict]: ...                       # keywords decoded back to list[str]

# dags/paper_lib/html_page.py (C)
def build_html(papers: list[dict], output_path: Path) -> None: ...         # rewrites the whole page

# dags/paper_lib/notify.py (C)
def notify_new_paper(webhook_url: str, record: dict) -> None: ...          # raises on HTTP error
```

`CATEGORIES`: Data Engineering, Machine Learning, Natural Language Processing, Computer Vision, Databases, Process Mining & BPM, Responsible AI, Other. B may adjust this list, since nothing outside `llm_metadata.py` depends on it.

### SQLite table

```sql
CREATE TABLE IF NOT EXISTS papers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filename     TEXT NOT NULL UNIQUE,
    title        TEXT NOT NULL,
    summary      TEXT NOT NULL,
    keywords     TEXT NOT NULL,                    -- JSON string, e.g. '["airflow", "llm"]'
    category     TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### DAG shape (A)

```text
ensure_db
   │
find_new_pdfs              list of new PDFs; ends the run early if empty
   │
process_paper [×N]         task group, one copy per new PDF:
   │                       convert_pdf ─► ask_llm ─► save_metadata
   │
render_html                once, after all papers, even if one of them failed
   │
notify_discord [×N]        one message per new paper that is now in the DB
```

| Task | Calls | Returns (XCom) |
|---|---|---|
| `ensure_db` | `init_db` | nothing |
| `find_new_pdfs` | `get_processed_filenames`, `list_new_pdfs` | list of new PDF paths |
| `process_paper.convert_pdf` | `pdf_to_markdown` | `{"filename", "md_path"}` |
| `process_paper.ask_llm` | `extract_metadata` | paper record |
| `process_paper.save_metadata` | `save_paper` | nothing |
| `render_html` | `get_all_papers`, `build_html` | nothing |
| `notify_discord` | `get_paper`, `notify_new_paper` | nothing |

Notes for A:

- "New" means a `.pdf` in `PAPERS_DIR` whose filename is not in the `papers` table yet. Optionally skip files modified in the last ~30 s: they may still be syncing, and the next run picks them up.
- With nothing new, end the run early (e.g. make `find_new_pdfs` a `@task.short_circuit`). The run is then a quick no-op and the page is not rewritten every 5 minutes.
- Map the whole task group (`@task_group` + `.expand()`), not each task on its own. Inside a mapped group, paper *i*'s `ask_llm` only waits for paper *i*'s `convert_pdf`, so one bad paper does not stop the others. Separately chained `.expand()` calls wait for every upstream copy instead.
- `render_html` needs `trigger_rule="all_done"` so the page is rebuilt even when one paper failed.
- Only small values go through XCom (paths, filenames, the metadata dict), never the Markdown text.
- Import `pymupdf4llm` and `openai` inside the task code, not at the top of the DAG file, so DAG parsing stays fast.
- Explain these choices in the report: they are what the 3 DAG points are about.

## 7. Repository layout

```text
paper-library/                 # GitHub repo, cloned inside WSL2 on the demo machine (e.g. ~/paper-library)
├── dags/
│   ├── paper_pipeline.py      # A: the scheduled DAG
│   └── paper_lib/             # importable from the DAG because Airflow puts dags/ on sys.path
│       ├── __init__.py
│       ├── config.py          # A
│       ├── scan.py            # A: list_new_pdfs, used by find_new_pdfs
│       ├── pdf_to_md.py       # B
│       ├── llm_metadata.py    # B
│       ├── storage.py         # C
│       ├── html_page.py       # C
│       └── notify.py          # C
├── tests/                     # pytest, one file per module, written by the module's owner
├── data/                      # git-ignored: papers.db, markdown/
├── docs/                      # architecture diagram and screenshots used in the README
├── .env.example               # every setting, no real secrets
├── .gitignore                 # .env, data/, *.db, *.pdf, virtualenvs, __pycache__/, logs
├── requirements.txt           # pinned versions
└── README.md
```

Google Drive, in A's account:

```text
ResearchLibrary/
├── papers/          # drop PDFs here (drive.google.com or the Drive app)
└── output/
    └── index.html   # written by the DAG
```

## 8. Technical notes

### Demo machine (A's PC)

Windows 11, Intel i5-12600KF, 32 GB RAM, NVIDIA RTX 4060 (8 GB). WSL2 with Ubuntu 24.04 and Python 3.12 is already installed, and the GPU is visible from WSL2. Still to install: Airflow, Ollama, Google Drive for Desktop.

**Airflow.** Airflow does not run natively on Windows, so it runs inside WSL2. Keep the repo and the virtualenv in the Linux file system (`~/`), not under `/mnt/c`, which is much slower.

```bash
python3 -m venv ~/venvs/airflow && source ~/venvs/airflow/bin/activate
AIRFLOW_VERSION=3.3.2        # pinned (requirements.txt and README)
PYTHON_VERSION=3.12
pip install "apache-airflow==${AIRFLOW_VERSION}" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
export AIRFLOW_HOME=~/airflow
export AIRFLOW__CORE__DAGS_FOLDER=~/paper-library/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
airflow standalone           # UI at http://localhost:8080 (also from the Windows browser); login printed in the terminal
```

Airflow 3 DAGs import from `airflow.sdk` (`from airflow.sdk import dag, task, task_group`).

**Ollama.** Install it inside WSL2 as well, so Airflow reaches it at `http://localhost:11434/v1` with no network setup: `curl -fsSL https://ollama.com/install.sh | sh`, then `ollama pull <model>`. If it is not running as a service, start `ollama serve` in a second terminal. `nvidia-smi` during a request should show GPU memory in use. 8 GB of VRAM fits a 7–8B model in 4-bit (e.g. `qwen2.5:7b`, `llama3.1:8b`).

**Google Drive for Desktop** (Windows side). Use *Mirror files* mode: the files are then normal files on `C:` that WSL2 sees under `/mnt/c/Users/<you>/My Drive/ResearchLibrary/`. Check the exact folder in Drive's settings, and quote the path because "My Drive" contains a space. Mirror mode downloads all of My Drive. If that is too big, use *Stream files* mode, make `ResearchLibrary` available offline and mount the drive in WSL2: `sudo mkdir -p /mnt/g && sudo mount -t drvfs G: /mnt/g`.

Keep the PC awake during scheduled runs and the demo.

### Local LLM (B)

- The code only depends on `LLM_BASE_URL` and `LLM_MODEL`, so Ollama (port 11434) and LM Studio (port 1234) are interchangeable during development.
- Small models have small context windows, and Ollama silently cuts prompts that are too long. Send only the beginning of the paper (or raise `OLLAMA_CONTEXT_LENGTH`).
- Use `response_format={"type": "json_object"}`, and also say in the prompt: return only a JSON object with the keys `title`, `summary`, `keywords`, `category`, with the category taken from this exact list.
- Avoid "thinking" models (they add text before the JSON), or turn thinking off.
- Temperature 0–0.2 for stable output.
- The retry-once inside `extract_metadata` is separate from Airflow's task retries. Keep both.
- On a weaker laptop, develop with a 3–4B model. The final runs use the demo machine's GPU.
- Measured on the demo machine (`qwen2.5:7b`, JSON mode): about 2 s per call once the model is loaded, about 45 s for the first call after a restart. In a quick test the model returned `keywords` as one comma-separated string instead of a list, so the type checks and the cleanup are needed.

### HTML page (C)

- Embed the data in the page as `<script type="application/json" id="papers-data">…</script>`. In the `json.dumps` output, replace `</` with `<\/` so a title cannot close the tag. In JS, render with `textContent`, not `innerHTML`: LLM output is untrusted text.
- Do not `fetch()` a separate JSON file. Browsers block that for pages opened from disk.
- Write `index.html.tmp`, then `os.replace()` it onto `index.html`, so Drive never syncs a half-written page.

### Discord (A and C)

- Creating a webhook: Server Settings → Integrations → Webhooks → New Webhook → Copy Webhook URL.
- Limits: message content 2,000 characters; embed title 256, embed description 4,096, field value 1,024.
- `requests.post(url, json=payload, timeout=10)`, then `raise_for_status()`, so a failed call fails the task and Airflow retries it.

## 9. Report (LaTeX on Prism) and README

The report should be short (aim for 4–6 pages): our approach, proof that the workflow runs correctly, and the GitHub link. We write it in LaTeX on OpenAI Prism. Prism is free with a ChatGPT account and runs in the browser, so everyone can edit at the same time without installing LaTeX.

Prism project layout. C creates it; each person edits only their own files:

```text
main.tex                       C: title page with the GitHub link, \input of every section
sections/1-introduction.tex    C
sections/2-architecture.tex    A
sections/3-dag.tex             A
sections/4-pdf-llm.tex         B
sections/5-outputs.tex         C
sections/6-proof.tex           A
sections/7-limitations.tex     B
figures/                       images; prefix file names with your role: a-grid-view.png, c-search.png, ...
```

| Section | Content | Writer |
|---|---|---|
| 1. Introduction | Goal, overview, GitHub link | C |
| 2. Architecture | Diagram, folder layout, tools and why we chose them | A |
| 3. Airflow DAG | Tasks, dependencies, schedule, new-file detection, mapped task group, retries, trigger rules | A |
| 4. PDF and LLM | Conversion, model choice, prompt, JSON mode, retry and validation, example output | B |
| 5. Storage and outputs | SQLite schema, HTML page (search, filter), Discord message | C |
| 6. Proof it works | Walkthrough of a real run on the demo machine, with screenshots | A |
| 7. Limitations and improvements | What can fail, what we would add next | B |

**Screenshots of the real run (A, demo machine):**

- [ ] Airflow Graph view (task dependencies)
- [ ] Grid view: several scheduled runs, including the mapped task group and a run with nothing new
- [ ] `ask_llm` log showing the LLM's JSON
- [ ] Drive folders `ResearchLibrary/papers/` and `output/`
- [ ] `index.html` from the real run: the full list, a search, a category filter
- [ ] Discord notifications from the real run
- [ ] Database content (e.g. `SELECT filename, title, category FROM papers;`)

**README** (graded together with the report). A creates these headings in the skeleton; each owner fills in their own:

| README section | Owner |
|---|---|
| Overview and architecture | A |
| Setup (WSL2, Airflow, Google Drive) | A |
| LLM setup | B |
| Discord webhook | C |
| Configuration (table of environment variables) | C |
| Run and test | A |
| Project structure | C |
| Outputs (database, web page, messages) | C |
| Troubleshooting | A |

## 10. Integration test checklist (A, demo machine)

- [ ] Empty DB and 3–4 PDFs in `papers/` → one run processes all of them: rows in the DB, entries on the page, messages in Discord.
- [ ] Next scheduled run with nothing new → quick no-op: no duplicates, no Discord message.
- [ ] Upload one of the kept-aside PDFs on drive.google.com → it syncs to the demo machine and is processed within ~5 minutes. This is the key demo for the report.
- [ ] Search and category filter work in `index.html` opened from the Drive folder.
- [ ] Broken or scanned PDF → that paper fails with a clear log; the other papers still go through.
- [ ] Restart Airflow → nothing is processed twice.
- [ ] `git log -p | grep -i "discord.com/api/webhooks"` finds nothing.

## 11. Final checklist (C, before uploading)

- [ ] The repo is public and opens in a private browser window. README run instructions are complete. No secrets, database or PDFs committed.
- [ ] Report PDF: short, explains the approach, shows the workflow running, GitHub link on the first page.
- [ ] Uploaded to UV → "Assignment 3" before Mon 9 Nov 12:00. A and B confirm that it is there.

## 12. Only if we are ahead

Anyone, in their own files, once their own checklist is done:

- Discord alert when a task fails (`on_failure_callback`).
- Remember PDFs that failed, so they are not retried every 5 minutes.
- Structured output with a JSON schema, if the server supports it.
- Show and sort by date added on the page.
