"""Driving Pi in RPC mode: one prompt in, its final answer out, and every way that can fail."""

from __future__ import annotations

import json
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARGV = ("--mode", "rpc", "--no-session")
INSTALL_HINT = (
    "pi not found on PATH; install it with `npm install -g @earendil-works/pi-coding-agent`"
)
STDERR_LINES = 20
SHUTDOWN_GRACE_S = 5.0


class PiMissingError(RuntimeError):
    """No `pi` binary on PATH; the message carries the install command."""


class PiFailedError(RuntimeError):
    """Pi rejected the prompt, or exited before its session settled."""


class PiTimeoutError(RuntimeError):
    """Pi did not settle within the deadline; the process tree was killed."""


@dataclass(frozen=True)
class TurnResult:
    """What one finished run produced: the text, the exit code, the tail of stderr."""

    text: str
    exit_code: int | None
    stderr_tail: str


def resolve_pi() -> str:
    """The `pi` binary on PATH, or `PiMissingError` carrying the install command."""
    found = shutil.which("pi")
    if not found:
        raise PiMissingError(INSTALL_HINT)
    return found


def run_turn(
    prompt: str, cwd: str | Path, timeout_s: float = 3600, pi: str | None = None
) -> TurnResult:
    """Run one prompt to the end of Pi's session and return its final text."""
    process = _spawn(pi or resolve_pi(), Path(cwd))
    records: queue.Queue[bytes | None] = queue.Queue()
    errors: deque[str] = deque(maxlen=STDERR_LINES)

    def note(raw: bytes) -> None:
        errors.append(raw.decode("utf-8", "replace"))

    _pump(process.stdout, records.put, done=lambda: records.put(None))
    _pump(process.stderr, note, done=lambda: None)
    try:
        _send(process, prompt)
        text = _collect(records, errors, timeout_s)
    except BaseException:
        _kill(process)
        raise
    return TurnResult(text=text, exit_code=_shutdown(process), stderr_tail=_tail(errors))


def _spawn(binary: str, cwd: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [binary, *ARGV],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(cwd),
        start_new_session=True,
    )


def _pump(stream: Any, sink: Callable[[Any], None], *, done: Callable[[], None]) -> None:
    def read() -> None:
        for raw in stream:
            line = raw.rstrip(b"\r\n")
            if line.strip():
                sink(line)
        done()

    threading.Thread(target=read, daemon=True).start()


def _send(process: subprocess.Popen, prompt: str) -> None:
    if process.stdin is None:
        raise PiFailedError("pi was started without a stdin pipe")
    record = {"id": "prompt-1", "type": "prompt", "message": prompt}
    process.stdin.write(json.dumps(record).encode("utf-8") + b"\n")
    process.stdin.flush()


def _collect(records: queue.Queue, errors: deque[str], timeout_s: float) -> str:
    deadline = time.monotonic() + timeout_s
    text = ""
    while True:
        raw = _next(records, deadline, timeout_s, errors)
        if raw is None:
            raise PiFailedError("pi exited before its session settled" + _suffix(errors))
        record = _parse(raw)
        if record.get("type") == "agent_settled":
            return text
        if record.get("type") == "message_end":
            text = _assistant_text(record) or text
        if record.get("type") == "response" and record.get("command") == "prompt":
            text = _prompt_response(record)
            if text is None:
                return ""


def _next(records: queue.Queue, deadline: float, timeout_s: float, errors: deque[str]) -> Any:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PiTimeoutError(f"pi timeout after {timeout_s:g}s" + _suffix(errors))
        try:
            return records.get(timeout=min(remaining, 0.5))
        except queue.Empty:
            continue


def _parse(raw: bytes) -> dict[str, Any]:
    try:
        record = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return record if isinstance(record, dict) else {}


def _prompt_response(record: dict[str, Any]) -> str | None:
    if record.get("success") is False:
        raise PiFailedError(str(record.get("error") or "pi rejected the prompt"))
    disposition = (record.get("data") or {}).get("disposition")
    return None if disposition == "handled" else ""


def _assistant_text(record: dict[str, Any]) -> str:
    message = record.get("message") or {}
    if message.get("role") != "assistant":
        return ""
    blocks = [block for block in message.get("content") or [] if block.get("type") == "text"]
    return "".join(str(block.get("text", "")) for block in blocks)


def _suffix(errors: deque[str]) -> str:
    return f"; stderr:\n{chr(10).join(errors)}" if errors else ""


def _tail(errors: deque[str]) -> str:
    return "\n".join(errors)


def _shutdown(process: subprocess.Popen) -> int | None:
    if process.stdin is not None and not process.stdin.closed:
        process.stdin.close()
    try:
        return process.wait(timeout=SHUTDOWN_GRACE_S)
    except subprocess.TimeoutExpired:
        _kill(process)
        return process.returncode


def _kill(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()
    process.wait()
