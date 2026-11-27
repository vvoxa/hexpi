"""The review gate: which run may close a card, and which reviewer a handoff goes to."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).parent.parent / "hooks" / "kanban-review-gate.py"


def board(tmp_path, current_run: int | None, claim: dict | None) -> Path:
    database = tmp_path / "kanban.db"
    conn = sqlite3.connect(database)
    conn.execute("CREATE TABLE tasks (id TEXT, current_run_id INT)")
    conn.execute("CREATE TABLE task_events (task_id TEXT, run_id INT, kind TEXT, payload TEXT)")
    conn.execute("INSERT INTO tasks VALUES ('t_1', ?)", (current_run,))
    if claim is not None:
        conn.execute(
            "INSERT INTO task_events VALUES ('t_1', ?, 'claimed', ?)",
            (current_run, json.dumps(claim)),
        )
    conn.commit()
    conn.close()
    return database


def gate(tool_name: str, *, board_db: Path | None = None, **tool_input) -> dict | None:
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    env = {
        "PATH": "/usr/bin:/bin",
        "HERMES_KANBAN_TASK": "t_1",
        "HERMES_KANBAN_DB": str(board_db) if board_db else "",
    }
    result = subprocess.run(
        [sys.executable, str(GATE)],
        check=False,
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else None


def test_an_implementation_run_cannot_close_its_card_and_is_told_the_way_out():
    directive = gate("kanban_complete", summary="done")
    assert directive is not None
    assert directive["action"] == "block"
    assert "kanban_request_review" in directive["message"]
    assert "'default'" in directive["message"]


def test_a_handoff_without_a_reviewer_is_routed_to_the_reviewing_profile():
    assert gate("kanban_request_review", summary="done") == {
        "action": "modify",
        "args": {"reviewer": "default"},
    }


def test_a_handoff_that_names_its_reviewer_is_left_alone():
    assert gate("kanban_request_review", summary="done", reviewer="researcher") is None


def test_the_review_run_may_close_the_card(tmp_path):
    database = board(tmp_path, 7, {"run_id": 7, "source_status": "review"})
    assert gate("kanban_complete", board_db=database, summary="approved") is None


def test_the_implementation_run_stays_blocked(tmp_path):
    database = board(tmp_path, 7, {"run_id": 7})
    directive = gate("kanban_complete", board_db=database, summary="done")
    assert directive is not None
    assert directive["action"] == "block"


def test_a_card_without_a_live_run_is_treated_as_an_implementation(tmp_path):
    database = board(tmp_path, None, None)
    directive = gate("kanban_complete", board_db=database, summary="done")
    assert directive is not None
    assert directive["action"] == "block"


def test_an_unreadable_board_does_not_open_the_gate(tmp_path):
    directive = gate("kanban_complete", board_db=tmp_path / "missing.db")
    assert directive is not None
    assert directive["action"] == "block"


def test_other_board_calls_pass_through():
    assert gate("kanban_block", reason="waiting") is None
