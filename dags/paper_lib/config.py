"""Settings for the paper pipeline, read from environment variables. Owner: A.

Values come from the process environment, or from a .env file at the repository
root (see .env.example). Variables already set in the environment win over .env.
Relative paths are resolved from the repository root, so every task sees the same
files whatever its working directory is.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


def _path(name: str, default: str) -> Path:
    path = Path(os.environ.get(name) or default).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


PAPERS_DIR: Path = _path("PAPERS_DIR", "data/papers")
OUTPUT_HTML: Path = _path("OUTPUT_HTML", "data/output/index.html")
DB_PATH: Path = _path("DB_PATH", "data/papers.db")
MARKDOWN_DIR: Path = _path("MARKDOWN_DIR", "data/markdown")
LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL") or "http://localhost:11434/v1"
LLM_MODEL: str = os.environ.get("LLM_MODEL") or "qwen2.5:7b"
DISCORD_WEBHOOK_URL: str = os.environ.get("DISCORD_WEBHOOK_URL") or ""
