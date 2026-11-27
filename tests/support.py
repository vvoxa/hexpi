"""Fakes and loaders the tests inject; production code never learns a test exists."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"
MODULE_NAME = "hexpi_under_test"


def load_plugin():
    """Import ``plugin/__init__.py`` as a package, the way the Hermes loader does."""
    spec = importlib.util.spec_from_file_location(
        MODULE_NAME, PLUGIN / "__init__.py", submodule_search_locations=[str(PLUGIN)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def declared_tools():
    """The tool names ``plugin.yaml`` promises, read from its flow-sequence line."""
    text = (PLUGIN / "plugin.yaml").read_text()
    line = next(row for row in text.splitlines() if row.startswith("provides_tools:"))
    return [name.strip() for name in line.partition(":")[2].strip().strip("[]").split(",") if name]


class FakeContext:
    """Stands in for the loader's context: records what ``register()`` asks for."""

    def __init__(self):
        self.tools = {}

    def register_tool(self, name, toolset, schema, handler, **extra):
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler, **extra}
