"""Research library pipeline (INFO-H420 Assignment 3).

Every 5 minutes: find the new PDFs in the Google Drive-synced papers folder, convert each
one to Markdown, ask the local LLM for its title, summary, keywords and category, save them
in SQLite, rebuild the static HTML page, and send one Discord message per new paper.
The task graph and the helper functions follow ROADMAP.md, section 6.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import TriggerRule, dag, task, task_group

from paper_lib import config


@dag(
    dag_id="paper_pipeline",
    schedule="*/5 * * * *",
    start_date=pendulum.datetime(2026, 11, 1, tz="Europe/Brussels"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["info-h420"],
    doc_md=__doc__,
)
def paper_pipeline():
    @task
    def ensure_db() -> None:
        """Create the SQLite database and the papers table if they do not exist yet."""
        from paper_lib.storage import init_db

        config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        init_db(config.DB_PATH)

    @task.short_circuit
    def find_new_pdfs() -> list[str]:
        """List the PDFs that are not in the database yet. An empty list skips the rest of the run."""
        from paper_lib.scan import list_new_pdfs
        from paper_lib.storage import get_processed_filenames

        new = list_new_pdfs(config.PAPERS_DIR, get_processed_filenames(config.DB_PATH))
        return [str(path) for path in new]

    @task_group
    def process_paper(pdf_path: str):
        """One copy per new PDF, so a failing paper does not stop the others."""

        @task
        def convert_pdf(pdf_path: str) -> dict:
            from paper_lib.pdf_to_md import pdf_to_markdown

            config.MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
            md_path = pdf_to_markdown(Path(pdf_path), config.MARKDOWN_DIR)
            return {"filename": Path(pdf_path).name, "md_path": str(md_path)}

        @task(execution_timeout=timedelta(minutes=10))
        def ask_llm(converted: dict) -> dict:
            from paper_lib.llm_metadata import extract_metadata

            markdown = Path(converted["md_path"]).read_text(encoding="utf-8")
            metadata = extract_metadata(markdown, config.LLM_BASE_URL, config.LLM_MODEL)
            return {"filename": converted["filename"], **metadata}

        @task
        def save_metadata(record: dict) -> None:
            from paper_lib.storage import save_paper

            metadata = {key: value for key, value in record.items() if key != "filename"}
            save_paper(config.DB_PATH, record["filename"], metadata)

        save_metadata(ask_llm(convert_pdf(pdf_path)))

    @task(trigger_rule=TriggerRule.ALL_DONE)
    def render_html() -> None:
        """Rebuild the whole page from the database, even when one of the papers failed."""
        from paper_lib.html_page import build_html
        from paper_lib.storage import get_all_papers

        config.OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
        build_html(get_all_papers(config.DB_PATH), config.OUTPUT_HTML)

    @task
    def notify_discord(pdf_path: str) -> None:
        """Send one Discord message for this paper, if it made it into the database."""
        from airflow.sdk.exceptions import AirflowSkipException

        from paper_lib.notify import notify_new_paper
        from paper_lib.storage import get_paper

        if not config.DISCORD_WEBHOOK_URL:
            raise AirflowSkipException("DISCORD_WEBHOOK_URL is not set")
        record = get_paper(config.DB_PATH, Path(pdf_path).name)
        if record is None:
            raise AirflowSkipException(f"{Path(pdf_path).name} is not in the database: it failed earlier")
        notify_new_paper(config.DISCORD_WEBHOOK_URL, record)

    new_pdfs = find_new_pdfs()
    ensure_db() >> new_pdfs
    papers = process_paper.expand(pdf_path=new_pdfs)
    page = render_html()
    papers >> page >> notify_discord.expand(pdf_path=new_pdfs)


paper_pipeline()
