# Agent notes

`hexpi` is a Hermes plugin: Hermes delegates a coding task, Pi does the work. The plugin is the whole product;
Pi and Hermes are dependencies we do not modify.

## Invariants

- **The user's `~/.pi` is never touched.** Every Pi invocation runs with `PI_CODING_AGENT_DIR` pointed at the
  plugin's own home. Reading the user's Pi config to "inherit" it is the same violation.
- **Pi is never configured by hand.** Provider, model, effort, codemode and credentials reach Pi as command-line
  arguments or as files inside the plugin's own home. The README's install section must stay true: no
  `pi auth login`, no `~/.pi/agent/settings.json` editing.
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

- `hermes plugins validate plugin/hexpi` and `hermes plugins doctor plugin/hexpi --ci` must pass; validate runs
  `register()` in a stripped host, so keep module import side-effect free.
- Tests are hermetic: plain asserts in `tests/`, run by `python3 tests/selfcheck.py`, no framework, no network,
  no real `pi` binary, no live provider. Stub the subprocess, assert on the argv it would have been started with
  and on the JSONL records exchanged — that is where the contract lives.
- Prove a negative claim before writing it down: "Pi does X when missing" needs a run that shows it, not a
  reading of the docs.

## Seams

- `register(ctx)` is the only entry point. `plugin.yaml` declares what `register()` actually does; the two are
  checked against each other, so keep them in step in the same commit.
- The delegation backend decides the route, never the process. If the task needs Pi to *be* the worker and the
  backend cannot express that, the answer is a different seam (profile route, terminal backend), not a provider
  that spawns processes behind Hermes' back.
- Pi talks to us in `--mode rpc`: JSONL on stdin and stdout, one record per line, `agent_settled` as the only
  completion signal. Parse by line, keep stderr for logs, and never let a protocol record share stdout with
  anything else.
- Cancellation must reach the process: a stopped subagent leaves no Pi running.

## Workflow

- Milestones from the README roadmap, one at a time, in order. Do not open the next one before the current one
  passes its checks.
- Research notes and implementation plans live in the vault (`projects/hexpi/`), never in this repository.
- Answer in the user's language; keep code, paths, commands and error strings verbatim.
