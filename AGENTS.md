# Agent notes

`hexpi` is a Hermes plugin: Hermes delegates a coding task, Pi does the work. The plugin is the whole product;
Pi and Hermes are dependencies we do not modify.

## Invariants

- **Pi owns its configuration.** Provider, model, effort, codemode and credentials are Pi's own settings; the
  plugin must not write them, copy them or override them, and its docs must not ask the user to reconfigure Pi
  for hexpi. The one argv element we add is `--no-session`, so our runs leave no history in Pi's home.
- **The plugin stays Python and standard library only.** A dependency is a decision that goes into
  `docs/stack.md` with the reason, before it goes into `pyproject.toml`.
- **Settings go through the Hermes config API** (`ctx.set_config`, `hermes_cli.config.set_config_value`), never
  through a hand edit of `config.yaml`. Every setting must render in the desktop settings pane and be settable
  with `hermes config set` — a setting that only works on one surface is half a setting.
- **No infrastructure specifics in tracked files.** No hostnames, domains, addresses, container names, panel
  URLs, or paths from a real machine. Placeholders: `<host>`, `$HERMES_HOME`, `REPLACE_ME`.
- **Comments are a defect.** `#` is banned outright (`tests/test_architecture.py` fails the build). What the
  code cannot say with names, types and tests goes in a docstring — and only a module's public API gets one,
  meaning what `__init__.py` calls or a test uses. An internal helper earns a better name instead of a
  sentence.

## Architecture

`docs/architecture.md` is the shape; these are the parts that are easy to break:

- **A module never imports another module of this plugin.** `__init__.py` is the composition root: it builds
  collaborators and passes them in. A module that needs something takes it as an argument.
- One component per file: parsing, protocol, and the tool's handler do not share a module.
- A file stays under 200 lines, a function under 40. A function that needs a banner comment is two functions.
- The plugin lives in `plugin/`; the repository root stays free of `__init__.py` so `pytest` never imports the
  checkout as a package (that breaks in a clone directory whose name is not an identifier).
- SOLID means: one reason to change per module, depend on the shape you use (a callable, not a class), no god
  object, depth over width.

## Tests

`docs/testing.md` is the process. The rules that decide whether a test is allowed to exist:

- **A test must fail when the behaviour disappears.** Name the expected RED before writing code.
- Few tests, about behaviours a user would recognise, named as claims ("a prompt returns the final assistant
  text"), never `test_happy_path`.
- Hermetic: no network, no real `pi`, no live provider. Fakes are scripted peers in `tests/support.py`; inject
  through the constructor, do not monkeypatch module globals.
- Assertions are frozen acceptance criteria: changing one is a `test!:` commit with the behaviour change
  spelled out. Never edit a test to make an implementation pass.
- No coverage target.

## Verification

- `hermes plugins validate plugin` and `hermes plugins doctor plugin --ci` must pass; validate runs `register()` in a
  stripped host, so keep module import side-effect free.
- `ruff check .`, `ruff format --check .`, `pytest -q` — all three, no filtering, before a commit.
- `tests/test_architecture.py` enforces the architecture rules above: sibling imports, sizes, and the absence
  of `#` comments. If it fails, fix the code, not the test.
- Prove a negative claim before writing it down: "Pi does X when missing" needs a run that shows it, not a
  reading of the docs.

## Seams

- `register(ctx)` is the only entry point. `plugin/plugin.yaml` declares what `register()` actually does; the
  two are checked against each other, so keep them in step in the same commit.
- This plugin is a **tool**, not a delegation backend: routing a subagent to a profile belongs to
  `advanced-delegation`'s `profile_routes`. Do not add a provider here — two owners for one decision.
- One tool, `pi`, in one toolset of its own. The profile's model decides to call it; the tool decides nothing
  about *how* Pi codes.
- Pi talks to us in `--mode rpc`: JSONL on stdin and stdout, one record per line, `agent_settled` as the only
  completion signal. Parse by line, keep stderr for logs, and never let a protocol record share stdout with
  anything else.
- Cancellation must reach the process: a stopped subagent leaves no Pi running.

## Workflow

- Milestones from the README roadmap, one at a time, in order. Do not open the next one before the current one
  passes its checks.
- Research notes and implementation plans live in the vault (`projects/hexpi/`), never in this repository.
- Commit messages are the changelog: `<type>(<scope>): <subject>` per Conventional Commits (`docs/releases.md`).
  A commit that does not follow it never reaches `CHANGELOG.md`, and the release PR is generated from them.
- Version, changelog and tag are produced by `release-please` from those commits — never bump a version or edit
  the changelog by hand.
- Answer in the user's language; keep code, paths, commands and error strings verbatim.
