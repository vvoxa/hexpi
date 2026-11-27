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

These live in `AGENTS.md` and `docs/architecture.md` because a linter cannot check them:

- **no `#` comments at all** — enforced by `tests/test_architecture.py`, not by ruff, because the rule is
  absolute here rather than a style preference;
- a docstring only on a module's public API, meaning what `__init__.py` calls or a test uses; it says what the
  function returns on failure, and it never restates the signature;
- no dependency without a line in this file explaining what it buys;
- a module never imports a sibling module; `__init__.py` is the only composition root.

## The two rules that outrank the linter

Ruff cannot see them, and they are the ones that decide whether the code survives:

1. **A test that would pass with the behaviour deleted is not a test** — `docs/testing.md`.
2. **A `# noqa` is a claim that the rule is wrong here.** It needs its reason on the same line; the ones we
   accepted on purpose are listed above so nobody re-litigates them per file.

## Why not a type checker yet

`mypy`/`pyright` would catch real defects, but the plugin's core is one subprocess protocol, and annotations
plus tests that assert on the exact JSONL cover it at this size. Revisit when the plugin has more than three
modules: then a strict `mypy` in CI is cheaper than the bug it prevents.
