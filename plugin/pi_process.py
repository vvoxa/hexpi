"""The Pi child process: find the binary, spawn it, pump its two streams, write, end it."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

ARGV = ("--mode", "rpc", "--no-session")
SHUTDOWN_GRACE_S = 5.0


def locate() -> str | None:
    """Where `pi` is on PATH, or None when it is not installed."""
    return shutil.which("pi")


def spawn(binary: str, cwd: Path) -> subprocess.Popen:
    """Start Pi in RPC mode as its own process group, so a kill takes its children with it."""
    return subprocess.Popen(
        [binary, *ARGV],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(cwd),
        start_new_session=True,
    )


def read_lines(stream: Any, sink: Callable[[bytes], None], *, done: Callable[[], None]) -> None:
    """Feed every LF-terminated line of ``stream`` to ``sink`` from a background thread."""

    def read() -> None:
        for raw in stream:
            line = raw.rstrip(b"\r\n")
            if line.strip():
                sink(line)
        done()

    threading.Thread(target=read, daemon=True).start()


def write(process: subprocess.Popen, record: dict[str, Any]) -> None:
    """Send one protocol record as one line, and make sure it left the buffer."""
    if process.stdin is None:
        raise RuntimeError("pi was started without a stdin pipe")
    process.stdin.write(json.dumps(record).encode("utf-8") + b"\n")
    process.stdin.flush()


def close(process: subprocess.Popen) -> int | None:
    """Ask Pi to shut down by closing its stdin, then wait; a survivor is killed."""
    if process.stdin is not None and not process.stdin.closed:
        process.stdin.close()
    try:
        return process.wait(timeout=SHUTDOWN_GRACE_S)
    except subprocess.TimeoutExpired:
        kill(process)
        return process.returncode


def kill(process: subprocess.Popen) -> None:
    """Kill Pi's whole process group: a coding agent starts children of its own."""
    if process.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()
    process.wait()
