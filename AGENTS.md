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
- **No comments.** A name, a type or a docstring carries the reason; a comment restating the code is a second
  copy of a fact, and a banner means the file holds two subjects.

## Verification

- `hermes plugins validate .` and `hermes plugins doctor . --ci` must pass; validate runs `register()` in a
  stripped host, so keep module import side-effect free.
- Tests are hermetic: plain asserts in `tests/`, run by `python3 tests/selfcheck.py`, no framework, no network,
  no real `pi` binary, no live provider. Stub the subprocess, assert on the argv it would have been started with
  and on the JSONL records exchanged — that is where the contract lives.
- Prove a negative claim before writing it down: "Pi does X when missing" needs a run that shows it, not a
  reading of the docs.

## Seams

- `register(ctx)` is the only entry point. `plugin.yaml` declares what `register()` actually does; the two are
  checked against each other, so keep them in step in the same commit.
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
