"""Every way a run can end badly: a refusal, a silence, an interrupt, a dead process."""

import pytest
from support import assert_exited, crossing, fake_pi, plugin_module
from test_rpc_turn import turn

pi_process = plugin_module("pi_process")
pi_rpc = plugin_module("pi_rpc")


def test_a_run_that_never_settles_times_out_and_kills_the_process(tmp_path):
    binary, _ = fake_pi(tmp_path, [{"sleep": 30}], pid_file=tmp_path / "pi.pid")

    with pytest.raises(pi_rpc.PiTimeoutError, match="deadline"):
        turn("do it", tmp_path, binary)

    assert_exited(int((tmp_path / "pi.pid").read_text()))


def test_a_stopped_run_tells_pi_to_abort_and_returns_cancelled(tmp_path):
    pid_file = tmp_path / "pi.pid"
    binary, log = fake_pi(tmp_path, [], pid_file=pid_file, settle_on_abort=True, linger=True)

    result = turn("do it", tmp_path, binary, stop=pid_file.exists)

    assert result.cancelled
    assert_exited(int((tmp_path / "pi.pid").read_text()))
    assert {"type": "abort"} in crossing(log)


def test_a_pi_that_ignores_abort_is_killed_after_the_grace_period(tmp_path, monkeypatch):
    monkeypatch.setattr(pi_rpc, "ABORT_GRACE_S", 0.2)
    pid_file = tmp_path / "pi.pid"
    binary, log = fake_pi(tmp_path, [], pid_file=pid_file, linger=True)

    result = turn("do it", tmp_path, binary, stop=pid_file.exists)

    assert result.cancelled
    assert_exited(int((tmp_path / "pi.pid").read_text()))
    assert {"type": "abort"} in crossing(log)


def test_a_run_that_exits_without_settling_reports_stderr(tmp_path):
    binary, _ = fake_pi(tmp_path, [{"type": "agent_end"}], stderr="pi: provider 401\n", exit_code=3)

    with pytest.raises(pi_rpc.PiFailedError, match="provider 401"):
        turn("do it", tmp_path, binary)


def test_a_missing_pi_names_the_install_command(tmp_path, monkeypatch):
    monkeypatch.setattr(pi_process, "locate", lambda: None)

    with pytest.raises(
        pi_rpc.PiMissingError, match="npm install -g @earendil-works/pi-coding-agent"
    ):
        turn("do it", tmp_path, None)
