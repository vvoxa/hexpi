"""The architecture rules from docs/architecture.md, as checks."""

import ast
import io
import pathlib
import tokenize

MAX_FILE_LINES = 200
MAX_FUNCTION_LINES = 40
PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent / "plugin"
COMPOSITION_ROOT = "__init__.py"


def plugin_modules():
    return sorted(path for path in PLUGIN_ROOT.glob("*.py") if path.name != COMPOSITION_ROOT)


def imported_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_no_module_imports_another_module_of_the_plugin():
    siblings = {path.stem for path in plugin_modules()}
    for path in plugin_modules():
        assert not (imported_names(ast.parse(path.read_text())) & siblings), (
            f"{path.name} imports a sibling module; only {COMPOSITION_ROOT} may"
        )


def test_every_file_and_function_stays_small():
    for path in plugin_modules():
        source = path.read_text()
        assert len(source.splitlines()) <= MAX_FILE_LINES, f"{path.name} is too long"
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                span = (node.end_lineno or node.lineno) - node.lineno
                assert span <= MAX_FUNCTION_LINES, f"{path.name}:{node.name} is too long"


def test_no_comments():
    for path in plugin_modules():
        comments = [
            token.string
            for token in tokenize.generate_tokens(io.StringIO(path.read_text()).readline)
            if token.type == tokenize.COMMENT
        ]
        assert not comments, f"{path.name} carries comments: {comments}"
