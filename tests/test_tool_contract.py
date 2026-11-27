"""What the `pi` tool promises Hermes: one declared tool, one toolset, a string back."""

import json
from types import SimpleNamespace

from support import FakeContext, crossing, declared_tools, fake_pi, load_plugin, plugin_module

pi_tool = plugin_module("pi_tool")


def message_end(text):
    return {
        "type": "message_end",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def registered():
    ctx = FakeContext()
    load_plugin().register(ctx)
    return ctx.tools


def test_the_manifest_declares_exactly_the_tools_register_provides():
    assert declared_tools() == sorted(registered())


def test_the_tool_sits_in_a_toolset_of_its_own_named_after_the_plugin():
    assert {name: tool["toolset"] for name, tool in registered().items()} == {"pi": "hexpi"}


def test_a_call_without_a_prompt_returns_an_error_instead_of_raising():
    answer = json.loads(registered()["pi"]["handler"]({}))

    assert answer["status"] == "error"
    assert "prompt" in answer["error"]


def test_a_finished_run_comes_back_as_the_text_pi_left():
    turn = lambda prompt, cwd: SimpleNamespace(text=f"did: {prompt}", exit_code=0)  # noqa: E731

    answer = json.loads(pi_tool.handler(turn)({"prompt": "rename the parser", "cwd": "/work"}))

    assert answer == {"status": "ok", "text": "did: rename the parser", "exit_code": 0}


def test_a_failed_run_reaches_the_model_as_an_error_string():
    def turn(prompt, cwd):
        raise RuntimeError("pi not found on PATH")

    answer = json.loads(pi_tool.handler(turn)({"prompt": "do it"}))

    assert answer == {"status": "error", "error": "pi not found on PATH"}


def test_the_registered_handler_runs_pi_in_rpc_mode_end_to_end(tmp_path, monkeypatch):
    settled = [
        message_end("renamed"),
        {"type": "agent_settled", "aborted": False},
    ]
    _, log = fake_pi(tmp_path, settled)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    ctx = FakeContext()

    load_plugin().register(ctx)
    answer = json.loads(
        ctx.tools["pi"]["handler"]({"prompt": "rename the parser", "cwd": str(tmp_path)})
    )

    assert answer == {"status": "ok", "text": "renamed", "exit_code": 0}
    assert crossing(log)[0]["argv"] == ["--mode", "rpc", "--no-session"]
