"""The protocol tests: framing by line only, completion, dialogs, and ids that stay correlated."""

import json

from support import plugin_module

pi_stream = plugin_module("pi_stream")


def message(role, content):
    return {"type": "message_end", "message": {"role": role, "content": content}}


def text(value):
    return {"type": "text", "text": value}


def test_a_record_that_contains_a_unicode_separator_survives_framing():
    raw = json.dumps(message("assistant", [text("a\u2028b")])).encode()

    assert pi_stream.final_text(pi_stream.parse(raw)) == "a\u2028b"


def test_a_trailing_carriage_return_does_not_break_the_record():
    raw = json.dumps({"type": "agent_settled", "aborted": False}).encode() + b"\r"

    assert pi_stream.is_settled(pi_stream.parse(raw.rstrip(b"\r")))


def test_a_line_that_is_not_json_is_ignored_rather_than_fatal():
    assert pi_stream.parse(b"Warning: no models available") is None


def test_agent_end_alone_is_not_completion():
    assert not pi_stream.is_settled({"type": "agent_end"})
    assert pi_stream.is_settled({"type": "agent_settled", "aborted": False})


def test_the_final_text_comes_only_from_a_finished_assistant_message():
    assert pi_stream.final_text({"type": "message_start", "message": {"content": []}}) is None
    assert pi_stream.final_text(message("user", "hi")) is None
    assert pi_stream.final_text(message("assistant", [text("ok")])) == "ok"


def test_two_text_blocks_of_one_message_are_joined_in_order():
    assert pi_stream.final_text(message("assistant", [text("a"), text("b")])) == "ab"


def test_a_dialog_gets_a_cancellation_and_a_notification_gets_nothing():
    select = {"type": "extension_ui_request", "id": "ui-1", "method": "select"}
    notify = {"type": "extension_ui_request", "id": "ui-2", "method": "notify"}

    assert pi_stream.dialog_answer(select) == {
        "type": "extension_ui_response",
        "id": "ui-1",
        "cancelled": True,
    }
    assert pi_stream.dialog_answer(notify) is None


def test_two_dialogs_in_one_run_are_answered_each_with_its_own_id():
    requests = [
        {"type": "extension_ui_request", "id": "ui-7", "method": "confirm"},
        {"type": "extension_ui_request", "id": "ui-9", "method": "editor"},
    ]

    assert [pi_stream.dialog_answer(record)["id"] for record in requests] == ["ui-7", "ui-9"]


def test_abort_is_a_bare_record_without_an_id():
    assert pi_stream.abort() == {"type": "abort"}
