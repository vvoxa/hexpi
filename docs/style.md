# Style

One authority: `ruff`, configured in `pyproject.toml`. Formatting is `ruff format`, not a discussion. This file
says *why* those rules, so a future agent can tell a deliberate rule from an accident.

## The rule set, in one line each

| Group | Why it is on |
|---|---|
| `E`, `W`, `F` | the baseline: syntax-level mistakes, unused names |
| `I` | import order — the one thing that makes diffs noisy when it drifts |
| `N` | naming — a name that lies is the most expensive defect to fix later |
| `UP` | modern syntax for the declared floor; keeps the codebase from ageing in place |
| `B` | bugbear: mutable defaults, closures over loop variables |
| `S` | bandit, because this plugin runs subprocesses and touches temp files |
| `A` | no shadowing `list`, `id`, `type` |
| `C4` | comprehensions over manual accumulation |
| `PTH` | `pathlib`, not string paths |
| `SIM`, `RET` | fewer shapes of the same logic |
| `ARG` | an unused argument is either a bug or a leftover |
| `TRY`, `G` | exception hygiene; `logging.exception` in an `except` is the pattern we want |
| `T20` | **no `print`** — stdout belongs to Pi's JSONL protocol in this plugin, so a stray print corrupts it |
| `DTZ` | no naive datetimes |
| `FBT` | no boolean positional parameters; a `bool` argument is unreadable at the call site |
| `ANN` | annotated signatures; the type is the first line of documentation |
| `PL` | pylint's useful subset, thresholds raised so it flags shapes, not length |
| `RUF` | ruff's own correctness rules, including unused `noqa` |

## Deliberate silences

Each one is a decision, and each is one line in `pyproject.toml`:

- `ANN401` — `Any` is honest at the plugin boundary: Hermes hands a handler `dict` and reads back `str`.
- `PLR0913` — a tool schema is a parameter list; the schema is the documentation.
- `S603`, `S607` — we build an argv list ourselves and `pi` is meant to come from `PATH`.
- `TRY003`, `EM101`, `EM102` — the error text is the message the model reads; a custom exception class adds a
  level of indirection and no information.
- `PLW2901` — rebinding a loop variable while parsing records is the clearest form of that loop.
- `tests/**` — asserts, no annotations, literal values: a test states facts, it does not model a domain.

## Rules that are not ruff's job

These live in `AGENTS.md` because a linter cannot check them:

- no comments that restate the code; a docstring carries what the code cannot;
- no dependency without a line in this file explaining what it buys;
- every public function's docstring says what it returns on failure.

## Why not a type checker yet

`mypy`/`pyright` would catch real defects, but the plugin's core is one subprocess protocol, and annotations
plus tests that assert on the exact JSONL cover it at this size. Revisit when the plugin has more than three
modules: then a strict `mypy` in CI is cheaper than the bug it prevents.
