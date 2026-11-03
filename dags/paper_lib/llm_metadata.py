"""Paper metadata from a locally served LLM. Owner: B.

STUB: returns fake metadata so the DAG can run end to end. B replaces the body
with the real call (openai client, JSON mode, retry once, type checks) and keeps
the signature from the contract.
"""
from __future__ import annotations

CATEGORIES: list[str] = [
    "Data Engineering",
    "Machine Learning",
    "Natural Language Processing",
    "Computer Vision",
    "Databases",
    "Process Mining & BPM",
    "Responsible AI",
    "Other",
]


def extract_metadata(markdown: str, base_url: str, model: str) -> dict:
    """Return the metadata dict. JSON mode + json.loads; retry once on bad JSON or
    missing/wrong-type fields; raise ValueError if the second attempt fails too."""
    first_line = next((line.lstrip("# ").strip() for line in markdown.splitlines() if line.strip()), "")
    return {
        "title": first_line or "Untitled (stub)",
        "summary": "Stub summary.",
        "keywords": ["stub"],
        "category": "Other",
    }
