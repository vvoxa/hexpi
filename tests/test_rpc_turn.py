"""One prompt in, Pi's final text out, and every way that can fail."""

import pytest
from support import crossing, fake_pi, plugin_module

pi_process = plugin_module("pi_process")
pi_rpc = plugin_module("pi_rpc")
pi_stream = plugin_module("pi_stream")
SETTLED = {"type": "agent_settled", "aborted": False}


def message_end(text):
    return {
        "type": "message_end",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def turn(prompt, cwd, binary, **extra):
    return pi_rpc.run_turn(prompt, cwd, 10, io=pi_process, stream=pi_stream, pi=binary, **extra)


def test_a_prompt_returns_the_final_assistant_text(tmp_path):
    binary, _ = fake_pi(tmp_path, [message_end("renamed 3 call sites"), SETTLED])

    assert turn("rename the parser", tmp_path, binary).text == "renamed 3 call sites"


def test_pi_runs_in_rpc_mode_without_a_session_and_gets_exactly_one_prompt(tmp_path):
    binary, log = fake_pi(tmp_path, [message_end("done"), SETTLED])

    turn("rename the parser", tmp_path, binary)

    argv, *sent = crossing(log)
    assert argv["argv"] == ["--mode", "rpc", "--no-session"]
    assert [record["type"] for record in sent] == ["prompt"]
    assert sent[0]["message"] == "rename the parser"
    assert sent[0]["id"] == "prompt-1"


def test_a_rejected_prompt_raises_with_pis_own_error(tmp_path):
    binary, _ = fake_pi(
        tmp_path,
        [
            {
                "type": "response",
                "id": "prompt-1",
                "command": "prompt",
                "success": False,
                "error": "Model not found: invalid/model",
            }
        ],
    )

    with pytest.raises(pi_rpc.PiFailedError, match="Model not found"):
        turn("do it", tmp_path, binary)


def test_an_answer_to_another_request_is_not_mistaken_for_ours(tmp_path):
    binary, _ = fake_pi(
        tmp_path,
        [
            {
                "type": "response",
                "id": "req-other",
                "command": "prompt",
                "success": False,
                "error": "stale",
            },
            message_end("fine"),
            SETTLED,
        ],
    )

    assert turn("do it", tmp_path, binary).text == "fine"


def test_a_prompt_nothing_handles_does_not_wait_for_a_run(tmp_path):
    binary, _ = fake_pi(
        tmp_path,
        [
            {
                "type": "response",
                "id": "prompt-1",
                "command": "prompt",
                "success": True,
                "data": {"disposition": "handled"},
            },
            SETTLED,
        ],
    )

    assert turn("/help", tmp_path, binary).text == ""


def test_a_dialog_is_answered_so_the_run_does_not_stall(tmp_path):
    binary, log = fake_pi(
        tmp_path,
        [
            {"type": "extension_ui_request", "id": "ui-4", "method": "confirm", "title": "run it?"},
            {"await_input": True},
            message_end("went ahead"),
            SETTLED,
        ],
    )

    assert turn("do it", tmp_path, binary).text == "went ahead"
    assert {"type": "extension_ui_response", "id": "ui-4", "cancelled": True} in crossing(log)


def test_agent_end_is_not_the_end_of_the_run(tmp_path):
    binary, _ = fake_pi(
        tmp_path,
        [
            message_end("first"),
            {"type": "agent_end"},
            {"sleep": 0.2},
            message_end("final"),
            SETTLED,
        ],
    )

    assert turn("do it", tmp_path, binary).text == "final"
