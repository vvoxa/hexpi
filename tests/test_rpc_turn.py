"""One prompt in, Pi's final text out, and every way that can fail."""

import pytest
from support import assert_exited, crossing, fake_pi, plugin_module

pi_rpc = plugin_module("pi_rpc")

SETTLED = {"type": "agent_settled", "aborted": False}


def message_end(text):
    return {
        "type": "message_end",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def test_a_prompt_returns_the_final_assistant_text(tmp_path):
    binary, _ = fake_pi(tmp_path, [message_end("renamed 3 call sites"), SETTLED])

    result = pi_rpc.run_turn("rename the parser", tmp_path, timeout_s=10, pi=binary)

    assert result.text == "renamed 3 call sites"


def test_pi_runs_in_rpc_mode_without_a_session_and_gets_exactly_one_prompt(tmp_path):
    binary, log = fake_pi(tmp_path, [message_end("done"), SETTLED])

    pi_rpc.run_turn("rename the parser", tmp_path, timeout_s=10, pi=binary)

    argv, *sent = crossing(log)
    assert argv["argv"] == ["--mode", "rpc", "--no-session"]
    assert [record["type"] for record in sent] == ["prompt"]
    assert sent[0]["message"] == "rename the parser"
    assert sent[0]["id"]


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
        pi_rpc.run_turn("do it", tmp_path, timeout_s=10, pi=binary)


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
            }
        ],
    )

    assert pi_rpc.run_turn("/help", tmp_path, timeout_s=10, pi=binary).text == ""


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

    assert pi_rpc.run_turn("do it", tmp_path, timeout_s=10, pi=binary).text == "final"


def test_a_run_that_never_settles_times_out_and_kills_the_process(tmp_path):
    binary, _ = fake_pi(tmp_path, [{"sleep": 30}], pid_file=tmp_path / "pi.pid")

    with pytest.raises(pi_rpc.PiTimeoutError, match="timeout"):
        pi_rpc.run_turn("do it", tmp_path, timeout_s=1, pi=binary)

    assert_exited(int((tmp_path / "pi.pid").read_text()))


def test_a_run_that_exits_without_settling_reports_stderr(tmp_path):
    binary, _ = fake_pi(tmp_path, [{"type": "agent_end"}], stderr="pi: provider 401\n", exit_code=3)

    with pytest.raises(pi_rpc.PiFailedError, match="provider 401"):
        pi_rpc.run_turn("do it", tmp_path, timeout_s=10, pi=binary)


def test_a_missing_pi_names_the_install_command(tmp_path, monkeypatch):
    monkeypatch.setattr(pi_rpc.shutil, "which", lambda _name: None)

    with pytest.raises(
        pi_rpc.PiMissingError, match="npm install -g @earendil-works/pi-coding-agent"
    ):
        pi_rpc.run_turn("do it", tmp_path, timeout_s=10)
