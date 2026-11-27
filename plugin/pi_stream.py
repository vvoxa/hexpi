"""What Pi's records mean: framing, completion, the final text, and the answer a dialog wants."""

from __future__ import annotations

import json
from typing import Any

DIALOG_METHODS = frozenset({"select", "confirm", "input", "editor"})


def parse(raw: bytes) -> dict[str, Any] | None:
    """One stdout line as a record; None when the line is not a JSON object (a stray line)."""
    try:
        record = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return record if isinstance(record, dict) else None


def is_settled(record: dict[str, Any]) -> bool:
    """Whether Pi has no remaining automatic work: the only completion signal worth waiting for."""
    return record.get("type") == "agent_settled"


def final_text(record: dict[str, Any]) -> str | None:
    """The text of a finished assistant message; None for any other record."""
    if record.get("type") != "message_end":
        return None
    message = record.get("message") or {}
    if message.get("role") != "assistant":
        return None
    blocks = [block for block in message.get("content") or [] if block.get("type") == "text"]
    return "".join(str(block.get("text", "")) for block in blocks)


def dialog_answer(record: dict[str, Any]) -> dict[str, Any] | None:
    """The reply a dialog needs — always a cancellation — or None when the request expects none."""
    if record.get("type") != "extension_ui_request":
        return None
    if record.get("method") not in DIALOG_METHODS:
        return None
    return {"type": "extension_ui_response", "id": record.get("id"), "cancelled": True}


def abort() -> dict[str, Any]:
    """Ask Pi to stop the run; it still answers `agent_settled`, so the caller keeps reading."""
    return {"type": "abort"}
