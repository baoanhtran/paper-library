"""Compare local models using role B's actual metadata extraction function.

From the repository root, for example:
    python docs/scripts/benchmark_llm.py --base-url http://localhost:11434/v1 \
        --model qwen2.5:3b --model qwen2.5:7b \
        --markdown docs/examples/sample-paper.md --runs 3 \
        --output data/benchmarks/llm-comparison.json

The supplied sample is synthetic. Use your own converted PDFs for an assessment
of paper quality. Requests go only to the endpoint supplied by --base-url;
use a local backend to keep source text on your machine.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
from time import perf_counter

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "dags"))

from paper_lib.llm_metadata import MAX_INPUT_CHARS, SYSTEM_PROMPT, extract_metadata  # noqa: E402


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure local models on the same Markdown excerpts; one model is a smoke run.",
        epilog="Example: python docs/scripts/benchmark_llm.py "
        "--model qwen2.5:3b --model qwen2.5:7b "
        "--markdown docs/examples/sample-paper.md --output data/benchmarks/results.json",
    )
    parser.add_argument("--base-url", default="http://localhost:11434/v1",
                        help="OpenAI-compatible endpoint (default: %(default)s)")
    parser.add_argument("--model", action="append", required=True, metavar="MODEL",
                        help="Exact backend model identifier; repeat to compare models")
    parser.add_argument("--markdown", type=Path, nargs="+", required=True, metavar="PATH",
                        help="One or more UTF-8 Markdown files; every model sees the same files")
    parser.add_argument("--runs", type=_positive_int, default=3,
                        help="Measured runs per paper and model (default: %(default)s)")
    parser.add_argument("--output", type=Path, default=Path("data/benchmarks/llm-comparison.json"),
                        help="JSON output, updated after each call (default: %(default)s)")
    return parser


def _summary(records: list[dict], models: list[str]) -> list[dict]:
    summaries = []
    for model in models:
        calls = [record for record in records if record["model"] == model]
        elapsed = [record["elapsed_seconds"] for record in calls if record["error"] is None]
        summaries.append({
            "model": model,
            "successful_calls": len(elapsed),
            "failed_calls": sum(record["error"] is not None for record in calls),
            "successful_latency_seconds": {
                "mean": statistics.mean(elapsed) if elapsed else None,
                "median": statistics.median(elapsed) if elapsed else None,
                "min": min(elapsed) if elapsed else None,
                "max": max(elapsed) if elapsed else None,
            },
        })
    return summaries


def _save(report: dict, output: Path) -> None:
    report["summary"] = _summary(report["results"], report["models"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    models = list(dict.fromkeys(model.strip() for model in args.model))
    if "" in models:
        parser.error("--model values must not be empty")
    if not args.base_url.strip():
        parser.error("--base-url must not be empty")

    papers = []
    for path in args.markdown:
        try:
            markdown = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            parser.error(f"cannot read {path}: {error}")
        if not markdown.strip():
            parser.error(f"Markdown file is empty: {path}")
        papers.append((path.resolve(), markdown))
    if args.output.resolve() in {path for path, _ in papers}:
        parser.error("--output must differ from every Markdown input")

    report = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "benchmark_kind": "model_comparison" if len(models) > 1 else "single_model_smoke",
        "base_url": args.base_url.strip(),
        "models": models,
        "runs_per_paper_and_model": args.runs,
        "max_input_characters": MAX_INPUT_CHARS,
        "system_prompt": SYSTEM_PROMPT,
        "environment": {
            "platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "python_version": platform.python_version(),
        },
        "notes": [
            "Measured wall time covers extract_metadata, including client setup and a validation retry if needed.",
            "PDF conversion and Markdown file reads are outside the timed interval.",
            "There is no warm-up call. The first call for each model may include loading; later calls may be warm.",
            "Actual model cache state depends on the backend; this script does not force loading or unloading.",
            "Inspect saved titles, categories, keywords and factual summaries against each source; latency alone is not quality.",
            "The bundled docs/examples/sample-paper.md fixture is synthetic, not a published research result.",
        ],
        "results": [],
    }
    _save(report, args.output)
    try:
        for model in models:
            call_index = 0
            for run in range(1, args.runs + 1):
                for path, markdown in papers:
                    call_index += 1
                    started = perf_counter()
                    metadata, error = None, None
                    try:
                        metadata = extract_metadata(markdown, args.base_url.strip(), model)
                    except Exception as failure:
                        error = {"type": type(failure).__name__, "message": str(failure)}
                    elapsed = perf_counter() - started
                    report["results"].append({
                        "model": model, "markdown_path": str(path), "run": run,
                        "first_call_for_model": call_index == 1,
                        "input_characters": len(markdown),
                        "source_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
                        "sent_characters": min(len(markdown), MAX_INPUT_CHARS),
                        "elapsed_seconds": round(elapsed, 6),
                        "metadata": metadata, "error": error,
                    })
                    _save(report, args.output)
                    print(f"{model} | {path.name} | run {run}/{args.runs} | "
                          f"{elapsed:.3f}s | {'error' if error else 'ok'}", file=sys.stderr)
    except KeyboardInterrupt:
        report["status"] = "interrupted"
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        _save(report, args.output)
        return 130

    failed = any(record["error"] is not None for record in report["results"])
    report["status"] = "completed_with_errors" if failed else "completed"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    _save(report, args.output)
    print(f"Saved comparison to {args.output}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
