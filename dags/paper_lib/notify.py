"""Discord webhook notification for a new paper. Owner: C.

STUB: logs instead of calling Discord so the DAG can run end to end. C replaces the
body with the real webhook call and keeps the signature from the contract.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def notify_new_paper(webhook_url: str, record: dict) -> None:
    """Send one Discord message for the paper record; raise on HTTP error."""
    log.info("Stub notification for %s", record.get("filename"))
