"""Run role B's PDF-to-metadata chain without Airflow.

Example, from the repository root:
    python docs/scripts/process_paper.py data/papers/sample.pdf \
        --output data/metadata/sample.json

Settings come from the existing configuration module and local .env. Explicit
--base-url, --model and --markdown-dir arguments override those defaults.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "dags"))

from paper_lib import config  # noqa: E402
from paper_lib.llm_metadata import extract_metadata  # noqa: E402
from paper_lib.pdf_to_md import pdf_to_markdown  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert one PDF and extract validated local LLM metadata.")
    parser.add_argument("pdf", type=Path, help="Text-based research PDF")
    parser.add_argument("--markdown-dir", type=Path, default=config.MARKDOWN_DIR,
                        help="Converted Markdown directory (default: MARKDOWN_DIR)")
    parser.add_argument("--base-url", default=config.LLM_BASE_URL,
                        help="Local OpenAI-compatible endpoint (default: LLM_BASE_URL)")
    parser.add_argument("--model", default=config.LLM_MODEL,
                        help="Loaded model identifier (default: LLM_MODEL)")
    parser.add_argument("--output", type=Path,
                        help="Optional JSON metadata file; metadata is also printed to stdout")
    args = parser.parse_args(argv)
    markdown_path = args.markdown_dir / f"{args.pdf.stem}.md"
    if args.output is not None and args.output.resolve() in {
        args.pdf.resolve(), markdown_path.resolve()
    }:
        parser.error("--output must differ from the source PDF and converted Markdown")

    markdown_path = pdf_to_markdown(args.pdf, args.markdown_dir)
    metadata = extract_metadata(
        markdown_path.read_text(encoding="utf-8"), args.base_url, args.model
    )
    serialized = json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Saved metadata to {args.output}", file=sys.stderr)
    # Escaped Unicode also works in Windows terminals without a UTF-8 code page.
    print(json.dumps(metadata, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
