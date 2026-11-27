"""The `pi` tool as Hermes sees it: its schema and the handler Hermes calls."""

from __future__ import annotations

import json
from typing import Any

SCHEMA: dict[str, Any] = {
    "name": "pi",
    "description": (
        "Hand a coding task to the Pi coding agent, which edits files in the working directory and "
        "reports what it did. Use it for work that changes a repository: writing, refactoring, "
        "running the project's own checks. One call is one task, and Pi owns the editing."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The task, in plain language."},
            "cwd": {
                "type": "string",
                "description": "Where Pi works. Defaults to the session's working directory.",
            },
        },
        "required": ["prompt"],
        "additionalProperties": False,
    },
}


def run(arguments: dict[str, Any]) -> str:
    """Return JSON with a ``status``: the work done, or why it is not done."""
    prompt = str(arguments.get("prompt") or "").strip()
    if not prompt:
        return json.dumps(
            {"status": "error", "error": "prompt is required: hand Pi the task to do"}
        )
    return json.dumps({"status": "not_implemented", "detail": "RPC client arrives in milestone 2"})
