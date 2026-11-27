"""Fakes and loaders the tests inject; production code never learns a test exists."""

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"
MODULE_NAME = "hexpi_under_test"
FAKE_PI = Path(__file__).resolve().parent / "fake_pi.py"


def _load(name, path, search=None):
    """Import once per run, so every test file sees the same module and exception classes."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path, submodule_search_locations=search)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_plugin():
    """Import ``plugin/__init__.py`` as a package, the way the Hermes loader does."""
    return _load(MODULE_NAME, PLUGIN / "__init__.py", [str(PLUGIN)])


def plugin_module(name):
    """Import one plugin module on its own, the way the composition root sees it."""
    return _load(f"{MODULE_NAME}.{name}", PLUGIN / f"{name}.py")


def declared_tools():
    """The tool names ``plugin.yaml`` promises, read from its flow-sequence line."""
    text = (PLUGIN / "plugin.yaml").read_text()
    line = next(row for row in text.splitlines() if row.startswith("provides_tools:"))
    return [name.strip() for name in line.partition(":")[2].strip().strip("[]").split(",") if name]


def fake_pi(
    directory, emit, stderr="", exit_code=0, pid_file=None, *, settle_on_abort=False, linger=False
):
    """A `pi` on PATH that speaks the recorded scenario: returns (binary, log path)."""
    directory = Path(directory)
    scenario = directory / "scenario.json"
    scenario.write_text(
        json.dumps(
            {
                "emit": emit,
                "stderr": stderr,
                "exit": exit_code,
                "settle_on_abort": settle_on_abort,
                "linger": linger,
            }
        )
    )
    log = directory / "pi.log"
    log.write_text("")
    pid_arg = f' --pid-file "{pid_file}"' if pid_file else ""
    binary = directory / "pi"
    binary.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_PI}" --scenario "{scenario}" --log "{log}"'
        f'{pid_arg} -- "$@"\n'
    )
    binary.chmod(0o755)
    return str(binary), log


def crossing(log):
    """Everything that crossed the pipe: the argv Pi ran with, then each stdin record."""
    return [json.loads(line) for line in Path(log).read_text().splitlines() if line.strip()]


class FakeContext:
    """Stands in for the loader's context: records what ``register()`` asks for."""

    def __init__(self, settings=None):
        self.tools = {}
        self.settings = {"timeout_s": 5, **(settings or {})}

    def register_tool(self, name, toolset, schema, handler, **extra):
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler, **extra}

    def get_config(self, key, default=None):
        return self.settings.get(key, default)


def assert_exited(pid, timeout_s=5.0):
    """Wait until the process is gone; a survivor fails the test that called it."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    raise AssertionError(f"process {pid} is still alive")
