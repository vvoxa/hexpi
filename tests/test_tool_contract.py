"""What the `pi` tool promises Hermes: one declared tool, one toolset, a string back."""

import json

from support import FakeContext, declared_tools, load_plugin


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


def test_every_call_returns_json_with_a_status():
    for arguments in ({}, {"prompt": "rename the parser", "cwd": "."}):
        answer = json.loads(registered()["pi"]["handler"](arguments))
        assert answer["status"] in {"error", "not_implemented", "ok"}
