# Testing

Tests are the specification. A behaviour that matters is written down once, as a test whose name is a sentence
about the system; everything else — comments, prose in a ticket, a paragraph in a docstring — is a second copy
that drifts. So: few tests, each one about something real, each one readable top to bottom without opening
another file.

## The one rule that shapes everything

**A test must fail when the behaviour disappears.** Write the test, watch it fail for the reason you expected,
then implement. A test that passes with the implementation deleted is not a test — it is decoration, and it will
keep passing after the feature is removed by someone else.

Corollary for agents: the failing output is named in the task before the code is written. "FAIL with
`PiMissing: pi not found on PATH`" is a RED; "tests are red" is not.

## Tooling: pytest, and nothing else

pytest is a **development** dependency. The plugin itself stays standard-library-only; `pyproject.toml` keeps
the two apart, so an installed plugin never pulls a test framework into a user's environment.

```bash
pip install ruff pytest           # the only two development tools
pytest -q                         # the whole suite
pytest -q -k "prompt"             # one subject
```

Why pytest and not a hand-rolled runner: readable failures (`assert "abc" == "abd"` shows the diff), one test
file per subject discovered automatically, `-k` for a single behaviour, and it is what any agent already knows
how to write. Why not `unittest`: more ceremony per test, worse output, nothing gained.

No coverage threshold. A number that says "87%" makes people write tests for getters. The gate is the mutant
rule above, checked by hand in review and by naming the RED in every task.

## Shape of a test file

`tests/test_<subject>.py`, one subject per file, and the subject is a behaviour a user would recognise:

| File | Subject |
|---|---|
| `test_tool_contract.py` | what the `pi` tool promises Hermes: schema, arguments, always a string back |
| `test_rpc_turn.py` | one prompt in, Pi's final text out |
| `test_rpc_protocol.py` | framing, ids, `agent_settled`, dialog replies |
| `test_rpc_failure.py` | missing binary, timeout, abort, stderr in the message |
| `test_architecture.py` | the import graph, file and function sizes, no comments |

Each test is named as a claim about the system, and the file reads as a list of claims:

```python
def test_a_prompt_returns_the_final_assistant_text(fake_pi):
    result = run_turn("rename the parser", cwd=Path("/tmp/x"), timeout_s=5, pi=fake_pi.binary)
    assert result.text == "renamed 3 call sites"
```

Not `test_run_turn_1`. Not `test_happy_path`. The name is the assertion in words.

## Hermetic, always

No network, no real `pi`, no real provider, no live service. A test that needs the outside world is an
integration probe and lives in a script a human runs, not in the suite.

The seam that makes this possible is the composition root: `pi_tool` receives a callable, so a test passes a
fake and never imports `pi_rpc`:

```python
def test_the_tool_returns_not_found_without_touching_pi():
    tool = pi_tool.handler(rpc=lambda prompt, cwd: PiMissing("pi not found on PATH"))
    assert json.loads(tool({"prompt": "hi"}))["status"] == "error"
```

`tests/support.py` holds the fakes and lives beside the tests, not in the plugin: production code never learns
that a test exists.

## What a fake looks like

`FakePi` is a **scripted peer**: it is a real object with `stdin`/`stdout`-shaped attributes that replays
recorded JSONL and records what was written to it. That way the test asserts on what actually crossed the
pipe — argv, the records sent, the records answered — which is the contract, not on internal calls:

```python
assert fake.argv == ["pi", "--mode", "rpc", "--no-session"]
assert fake.received == [{"id": "1", "type": "prompt", "message": "rename the parser"}]
assert fake.sent_back == [{"type": "extension_ui_response", "id": "ui-1", "cancelled": True}]
```

Do not mock by monkeypatching module globals `pi_rpc` reads; that couples the test to internals and breaks on
every refactor. Inject through the constructor, or stub the one system call (`shutil.which`) at the boundary.

## Tests are frozen acceptance criteria

The assertions are the contract. Changing one is a decision, not a cleanup:

- a changed assertion requires the `test!:` commit type and one line saying which behaviour changed and why;
- an implementation change that a test forbids means the test was right and the implementation is wrong — argue
  with the test, not around it;
- deleting a test is the same as deleting a feature and gets the same scrutiny.

This is what keeps the suite meaningful when an agent writes both sides.

## What we do not test

- private helpers — if it needs its own test, it is a module with a public entry point;
- Python itself (that `dict` works), the framework, or the manifest parser;
- every error branch of a subprocess (only the ones a user can hit: missing binary, timeout, abort);
- formatting and lint (ruff's job, and CI runs it).

## Sizes

A test file stays under ~120 lines; a test function under 15 lines. A test that needs a table of
`assert`s with comments to explain them is two behaviours sharing a name — split it, and the names
will tell you how.
