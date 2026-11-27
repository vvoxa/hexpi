"""The review gate: what the implementer profile may and may not do when it finishes a card."""

import json
import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).parent.parent / "hooks" / "kanban-review-gate.py"


def gate(tool_name: str, **tool_input) -> dict | None:
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    result = subprocess.run(
        [sys.executable, str(GATE)],
        check=False,
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else None


def test_completing_a_card_is_refused_and_the_refusal_names_the_way_out():
    directive = gate("kanban_complete", summary="done")
    assert directive is not None
    assert directive["action"] == "block"
    assert "kanban_request_review" in directive["message"]
    assert 'reviewer="default"' in directive["message"]


def test_a_handoff_without_a_reviewer_is_routed_to_the_reviewing_profile():
    assert gate("kanban_request_review", summary="done") == {
        "action": "modify",
        "args": {"reviewer": "default"},
    }


def test_a_handoff_that_names_its_reviewer_is_left_alone():
    assert gate("kanban_request_review", summary="done", reviewer="researcher") is None


def test_other_board_calls_pass_through():
    assert gate("kanban_block", reason="waiting") is None
