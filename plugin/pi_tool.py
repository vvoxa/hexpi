"""The `pi` tool as Hermes sees it: its schema and the handler Hermes calls."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

Turn = Callable[..., Any]

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


def handler(turn: Turn) -> Callable[[dict[str, Any]], str]:
    """Build the handler around one ``turn(prompt, cwd)`` callable, which is all it knows of Pi."""

    def run(arguments: dict[str, Any]) -> str:
        return _answer(arguments or {}, turn)

    return run


def _answer(arguments: dict[str, Any], turn: Turn) -> str:
    prompt = str(arguments.get("prompt") or "").strip()
    if not prompt:
        return json.dumps(
            {"status": "error", "error": "prompt is required: hand Pi the task to do"}
        )
    cwd = Path(str(arguments.get("cwd") or ".")).expanduser()
    try:
        result = turn(prompt, cwd)
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc) or type(exc).__name__})
    status = "cancelled" if getattr(result, "cancelled", False) else "ok"
    return json.dumps({"status": status, "text": result.text, "exit_code": result.exit_code})
