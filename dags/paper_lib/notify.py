"""Discord webhook notification for a new paper. Owner: C.

One message (one embed) per paper: title, category, keywords, short summary, filename.
Uses only the standard library. Field lengths stay below Discord's embed limits.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10

# Discord embed limits: title 256, description 4096, field value 1024, footer 2048,
# 6000 characters in total. We stay well below them.
TITLE_MAX = 256
SUMMARY_MAX = 600          # "short summary"
KEYWORDS_MAX = 1024
FOOTER_MAX = 200


def _truncate(text: str, limit: int) -> str:
    text = " ".join(str(text).split())  # collapse newlines and runs of spaces
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build_payload(record: dict) -> dict:
    """Webhook JSON body for one paper record."""
    keywords = ", ".join(record.get("keywords") or []) or "—"
    return {
        "username": "Research Library",
        "allowed_mentions": {"parse": []},  # paper text can never ping @everyone
        "embeds": [
            {
                "title": _truncate("📄 " + (record.get("title") or "Untitled"), TITLE_MAX),
                "description": _truncate(record.get("summary") or "", SUMMARY_MAX),
                "color": 0x2F5BEA,
                "fields": [
                    {"name": "Category", "value": _truncate(record.get("category") or "—", 256), "inline": True},
                    {"name": "Keywords", "value": _truncate(keywords, KEYWORDS_MAX), "inline": False},
                ],
                "footer": {"text": _truncate(record.get("filename") or "", FOOTER_MAX)},
            }
        ],
    }


def notify_new_paper(webhook_url: str, record: dict) -> None:
    """Send one Discord message for the paper record; raise on HTTP error."""
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(build_payload(record)).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            # Discord (Cloudflare) rejects the default "Python-urllib" agent with HTTP 403.
            "User-Agent": "paper-library-pipeline/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            response.read()
    except urllib.error.HTTPError as err:  # keep Discord's explanation in the Airflow log
        body = err.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Discord webhook returned HTTP {err.code}: {body}") from err
    log.info("Discord notified for %s", record.get("filename"))
