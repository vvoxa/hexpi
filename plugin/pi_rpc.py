"""The RPC client: one prompt in, the run followed to its end, every way out.

Record meaning and process start come from the composition root, so this module owns only the run:
deadline, answers, cancellation. `stop` is a zero-argument callable answering "should the run end?";
the plugin passes the host's own interrupt check.
"""

from __future__ import annotations

import queue
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROMPT_ID = "prompt-1"
INSTALL_HINT = (
    "pi not found on PATH; install it with `npm install -g @earendil-works/pi-coding-agent`"
)
STDERR_LINES = 20
ABORT_GRACE_S = 5.0
POLL_S = 0.25


class PiMissingError(RuntimeError):
    """No `pi` binary on PATH; the message carries the install command."""


class PiFailedError(RuntimeError):
    """Pi rejected the prompt, or exited before its session settled."""


class PiTimeoutError(RuntimeError):
    """Pi did not settle within the deadline; the process tree was killed."""


class PiCancelledError(RuntimeError):
    """The caller asked the run to stop; Pi was told to abort and the process tree was killed."""


@dataclass(frozen=True)
class TurnResult:
    """What one finished run produced: the text, the exit code, the tail of stderr."""

    text: str
    exit_code: int | None
    stderr_tail: str
    cancelled: bool = False


def run_turn(
    prompt: str,
    cwd: str | Path,
    timeout_s: float = 3600,
    *,
    io: Any,
    stream: Any,
    pi: str | None = None,
    stop: Any = None,
) -> TurnResult:
    """Run one prompt to the end of Pi's session and return its final text."""
    process = io.spawn(pi or _resolve(io), Path(cwd))
    records: queue.Queue[bytes | None] = queue.Queue()
    errors: deque[str] = deque(maxlen=STDERR_LINES)

    def note(raw: bytes) -> None:
        errors.append(raw.decode("utf-8", "replace"))

    io.read_lines(process.stdout, records.put, done=lambda: records.put(None))
    io.read_lines(process.stderr, note, done=lambda: None)
    try:
        io.write(process, {"id": PROMPT_ID, "type": "prompt", "message": prompt})
        text = _follow(process, records, errors, io, stream, time.monotonic() + timeout_s, stop)
    except KeyboardInterrupt:
        _end(process, records, io, stream)
        raise
    except PiCancelledError:
        _end(process, records, io, stream)
        return TurnResult("", None, "\n".join(errors), cancelled=True)
    except BaseException:
        io.kill(process)
        raise
    return TurnResult(text=text, exit_code=io.close(process), stderr_tail="\n".join(errors))


def _resolve(io: Any) -> str:
    found = io.locate()
    if not found:
        raise PiMissingError(INSTALL_HINT)
    return found


def _follow(
    process: Any,
    records: queue.Queue,
    errors: deque[str],
    io: Any,
    stream: Any,
    deadline: float,
    stop: Any,
) -> str:
    text = ""
    while True:
        record = stream.parse(_next(records, errors, deadline, stop))
        if record is None:
            continue
        answer = stream.dialog_answer(record)
        if answer is not None:
            io.write(process, answer)
            continue
        if stream.is_settled(record):
            return text
        message = stream.final_text(record)
        if message is not None:
            text = message or text
        if _rejected(record):
            raise PiFailedError(str(record.get("error") or "pi rejected the prompt"))


def _next(records: queue.Queue, errors: deque[str], deadline: float, stop: Any) -> bytes:
    while True:
        if stop is not None and stop():
            raise PiCancelledError("pi run cancelled by the caller")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PiTimeoutError("pi did not settle before the deadline" + _suffix(errors))
        try:
            raw = records.get(timeout=min(remaining, POLL_S))
        except queue.Empty:
            continue
        if raw is None:
            raise PiFailedError("pi exited before its session settled" + _suffix(errors))
        return raw


def _rejected(record: dict[str, Any]) -> bool:
    return (
        record.get("type") == "response"
        and record.get("command") == "prompt"
        and record.get("id") == PROMPT_ID
        and record.get("success") is False
    )


def _end(process: Any, records: queue.Queue, io: Any, stream: Any) -> None:
    """Stop Pi for good: abort and let it exit, or kill what is left after the grace period."""
    if _abort(process, records, io, stream):
        io.close(process)
    else:
        io.kill(process)


def _abort(process: Any, records: queue.Queue, io: Any, stream: Any) -> bool:
    """Tell Pi to stop; True when it settled by itself, False when it has to be killed."""
    io.write(process, stream.abort())
    deadline = time.monotonic() + ABORT_GRACE_S
    while time.monotonic() < deadline:
        try:
            raw = records.get(timeout=POLL_S)
        except queue.Empty:
            continue
        if raw is None or stream.is_settled(stream.parse(raw) or {}):
            return True
    return False


def _suffix(errors: deque[str]) -> str:
    return f"; stderr:\n{chr(10).join(errors)}" if errors else ""
