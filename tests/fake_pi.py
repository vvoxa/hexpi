"""A scripted peer that speaks Pi's RPC protocol: same argv, same records, no real Pi.

Invoked as ``fake_pi.py --scenario <json> --log <path> [--pid-file <path>] -- <pi argv...>``.

The scenario is a JSON object with ``emit``, ``stderr``, ``exit``, ``linger`` and
``settle_on_abort``. The first stdin line triggers the scripted replies, one JSON line each:
``{"sleep": s}`` waits instead of emitting, ``{"await_input": true}`` reads one more stdin line
first. ``linger`` keeps the process reading stdin afterwards; ``settle_on_abort`` answers an
``abort`` record with ``agent_settled``. Every stdin line lands in the log with the argv, so a test
can assert on what crossed the pipe.
"""

import json
import os
import sys
import time
from pathlib import Path

SETTLED_AFTER_ABORT = {"type": "agent_settled", "aborted": True}


def option(name: str) -> Path:
    return Path(sys.argv[sys.argv.index(name) + 1])


def record(path: Path, payload: object) -> None:
    with path.open("a") as handle:
        handle.write(json.dumps(payload) + "\n")


def emit(step: dict) -> None:
    sys.stdout.write(json.dumps(step) + "\n")
    sys.stdout.flush()


def main() -> int:
    scenario = json.loads(option("--scenario").read_text())
    log = option("--log")
    record(log, {"argv": sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []})
    if "--pid-file" in sys.argv:
        option("--pid-file").write_text(str(os.getpid()))
    lines = sys.stdin
    for line in lines:
        if not line.strip():
            continue
        received = json.loads(line)
        record(log, received)
        if received.get("type") == "abort" and scenario.get("settle_on_abort"):
            emit(SETTLED_AFTER_ABORT)
            continue
        for step in scenario.get("emit", []):
            if "sleep" in step:
                time.sleep(step["sleep"])
            elif step.get("await_input"):
                record(log, json.loads(lines.readline()))
            else:
                emit(step)
        if not scenario.get("linger"):
            break
    if scenario.get("stderr"):
        sys.stderr.write(scenario["stderr"])
    return int(scenario.get("exit", 0))


if __name__ == "__main__":
    raise SystemExit(main())
