"""Structure of the paper_pipeline DAG. Skipped where Airflow is not installed (B and C don't need it)."""
from pathlib import Path

import pytest

pytest.importorskip("airflow")

from airflow.dag_processing.dagbag import BundleDagBag  # noqa: E402
from airflow.sdk.definitions.taskgroup import MappedTaskGroup  # noqa: E402

DAGS_DIR = Path(__file__).resolve().parents[1] / "dags"


@pytest.fixture(scope="module")
def dag():
    # BundleDagBag puts dags/ on sys.path, like the DAG processor and the task runner do
    bag = BundleDagBag(dag_folder=str(DAGS_DIR), bundle_path=DAGS_DIR)
    assert bag.import_errors == {}
    return bag.dags["paper_pipeline"]


def test_run_settings(dag):
    assert dag.timetable.expression == "*/5 * * * *"
    assert dag.catchup is False
    assert dag.max_active_runs == 1
    assert dag.default_args["retries"] == 1


def test_task_ids(dag):
    assert set(dag.task_ids) == {
        "ensure_db",
        "find_new_pdfs",
        "process_paper.convert_pdf",
        "process_paper.ask_llm",
        "process_paper.save_metadata",
        "render_html",
        "notify_discord",
    }


def test_dependencies(dag):
    def upstream(task_id):
        return dag.get_task(task_id).upstream_task_ids

    assert upstream("find_new_pdfs") == {"ensure_db"}
    assert upstream("process_paper.convert_pdf") == {"find_new_pdfs"}
    assert upstream("process_paper.ask_llm") == {"process_paper.convert_pdf"}
    assert upstream("process_paper.save_metadata") == {"process_paper.ask_llm"}
    assert upstream("render_html") == {"process_paper.save_metadata"}
    assert upstream("notify_discord") == {"find_new_pdfs", "render_html"}


def test_each_paper_gets_its_own_copy_of_the_group(dag):
    assert isinstance(dag.task_group_dict["process_paper"], MappedTaskGroup)


def test_page_is_rebuilt_even_if_a_paper_failed(dag):
    assert dag.get_task("render_html").trigger_rule == "all_done"
