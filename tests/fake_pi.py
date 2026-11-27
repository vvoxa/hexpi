"""A scripted peer that speaks Pi's RPC protocol: same argv, same records, no real Pi.

Invoked as ``fake_pi.py --scenario <json> --log <path> [--pid-file <path>] -- <pi argv...>``.

The scenario is ``{"emit": [...], "stderr": "...", "exit": N, "linger": bool}``. The first stdin
line triggers the scripted replies, one JSON line each; ``{"sleep": s}`` waits instead of emitting,
``{"await_input": true}`` reads one more stdin line first. With ``linger`` the process stays alive
afterwards; without it, it exits. Every stdin line lands in the log behind one record naming the
argv, so a test can assert on what crossed the pipe.
"""

import json
import os
import sys
import time
from pathlib import Path


def option(name: str) -> Path:
    return Path(sys.argv[sys.argv.index(name) + 1])


def record(path: Path, payload: object) -> None:
    with path.open("a") as handle:
        handle.write(json.dumps(payload) + "\n")


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
        record(log, json.loads(line))
        for step in scenario.get("emit", []):
            if "sleep" in step:
                time.sleep(step["sleep"])
            elif step.get("await_input"):
                lines.readline()
            else:
                sys.stdout.write(json.dumps(step) + "\n")
                sys.stdout.flush()
        if not scenario.get("linger"):
            break
    if scenario.get("stderr"):
        sys.stderr.write(scenario["stderr"])
    return int(scenario.get("exit", 0))


if __name__ == "__main__":
    raise SystemExit(main())
