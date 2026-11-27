#!/usr/bin/env python3
"""A pre_tool_call hook that keeps a card from being closed by the run that wrote it.

The gate reads the card's current run from the board database, so it can tell an implementation run
from a review run without knowing which profile is installed. An implementation run loses
`kanban_complete` and is told to hand the card over; `kanban_request_review` gets `reviewer` filled
in, which reassigns the card so the review lane spawns the profile that can read the diff, run the
tests and hold the memory. A review run is left alone, because that is the run the gate exists for.
"""

import json
import os
import sqlite3
import sys

COMPLETE_REFUSAL = (
    "kanban_complete is closed for an implementation run: an implementer never accepts its own "
    "work. Hand the card over with kanban_request_review(reviewer={reviewer!r}, "
    "summary=<what you verified and what the reviewer should look at first>). "
    "The review lane closes it."
)


def card_and_run(payload: dict) -> tuple[str, str]:
    """``(database, task_id)`` for the card this call belongs to; empty strings when unknown."""
    extra = payload.get("extra") or {}
    return (
        os.environ.get("HERMES_KANBAN_DB", ""),
        os.environ.get("HERMES_KANBAN_TASK") or str(extra.get("kanban_task_id") or ""),
    )


def claim_payload(database: str, task_id: str) -> str | None:
    """The claim record of the card's live run, or None when it cannot be read."""
    try:
        conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=5)
    except sqlite3.Error:
        return None
    try:
        row = conn.execute("SELECT current_run_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None or row[0] is None:
            return None
        claim = conn.execute(
            "SELECT payload FROM task_events WHERE task_id = ? AND run_id = ? AND kind = 'claimed' "
            "ORDER BY rowid DESC LIMIT 1",
            (task_id, int(row[0])),
        ).fetchone()
        return claim[0] if claim else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def review_lane(database: str, task_id: str) -> bool:
    """Whether the card's live run was claimed out of the review column; False when unreadable."""
    if not (database and task_id):
        return False
    raw = claim_payload(database, task_id)
    if raw is None:
        return False
    try:
        return json.loads(raw or "{}").get("source_status") == "review"
    except json.JSONDecodeError:
        return False


def main() -> int:
    payload = json.load(sys.stdin)
    name = payload.get("tool_name") or ""
    args = payload.get("tool_input") or {}
    if name not in {"kanban_complete", "kanban_request_review"}:
        return 0
    reviewer = args.get("reviewer") or "default"
    database, task_id = card_and_run(payload)
    if review_lane(database, task_id):
        return 0
    if name == "kanban_complete":
        refusal = COMPLETE_REFUSAL.format(reviewer=reviewer)
        print(json.dumps({"action": "block", "message": refusal}))
    elif not args.get("reviewer"):
        print(json.dumps({"action": "modify", "args": {"reviewer": reviewer}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
