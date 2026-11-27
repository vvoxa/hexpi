# hexpi

**Hermes × Pi.** A Hermes plugin that makes [Pi](https://docs.pi.dev) — a terminal coding agent — a native
coding subagent of Hermes.

> **Status: pre-alpha.** Design only. Nothing is implemented yet; the roadmap below is the plan of record.

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [How it works](#how-it-works)
- [Roadmap](#roadmap)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Overview

Hermes spawns subagents through `delegate_task`. Those subagents are Hermes agents: their tools are Hermes
tools, their file edits go through Hermes' file operations, and their coding ability is whatever the model
brings. Pi is a coding agent built for exactly that job — it reads, edits, greps, runs commands and drives its
own loops.

`hexpi` puts the two together: a subagent that Hermes sees and manages like any other, but whose work is done
by Pi. The plugin registers a delegation backend and a profile-shaped subagent description, so Pi shows up in
the Hermes settings as one selectable coding subagent — in the desktop app and in the CLI alike.

Everything Pi needs is configured from Hermes: provider, model, reasoning effort, codemode, the Pi home
directory. Pi itself is never configured by hand, and the user's own `~/.pi` is never touched.

## Features

- **Pi as a native subagent.** The delegate task is handled by Pi, not by another Hermes agent.
- **Profiled, like a real subagent.** `hexpi` carries a description ("coding"), its own model/provider/effort
  route and its own home directory — an ephemeral profile: created on the fly, no state kept between tasks.
- **Deep integration with Hermes.** Pi gets the Hermes skills and the Hermes memory providers, so it works
  with the same knowledge the rest of the fleet does instead of starting from zero.
- **Forced codemode.** One switch turns on Pi's `codemode` tool (JavaScript that calls the other tools) for
  every run.
- **Configured from Hermes.** Provider, model, reasoning effort and API credentials are passed to Pi on the
  command line; no `pi auth login`, no `~/.pi/agent/settings.json` editing.
- **Pi installed on demand.** Missing from `PATH`? `hexpi` installs it.
- **Its own home.** `hexpi` keeps Pi's config, sessions and packages under its own directory, so the user's Pi
  installation stays untouched and no session litter accumulates.
- **Both surfaces.** Every setting works in the Hermes desktop app and in `hermes` on the command line.

## Requirements

- Hermes Agent 0.23.0 or newer (plugin and delegation-backend APIs)
- Python 3.11+ (the Hermes runtime; the plugin uses the standard library only)
- Network access on first run if Pi has to be installed
- A provider credential for the model Pi will use — held by Hermes, passed to Pi per run

## Installation

Not yet installable — the plugin skeleton lands in milestone 1. Target flow:

```bash
hermes plugins install <owner>/hexpi
hermes plugins validate hexpi
hermes config set delegation.backend hexpi
```

## Configuration

Settings live under `plugins.entries.hexpi.settings` — the same tree the desktop settings pane renders and
`hermes config set` writes.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `description` | str | `coding` | What the subagent is for, as the settings pane shows it |
| `home` | str | `<HERMES_HOME>/hexpi/pi` | Pi's home for `hexpi` (`PI_CODING_AGENT_DIR`). Never `~/.pi` |
| `pi_bin` | str | *(from `PATH`)* | Explicit Pi executable |
| `auto_install` | bool | `true` | Install Pi when it is missing |
| `provider` | str | *(inherited)* | Provider name passed to `--provider` |
| `model` | str | *(inherited)* | Model id passed to `--model` |
| `thinking` | str | *(unset)* | `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` → `--thinking` |
| `codemode` | bool | `true` | Force Pi's `codemode` tool on |
| `skills` | bool | `true` | Expose the Hermes skills to Pi |
| `memory` | bool | `true` | Expose the Hermes memory providers to Pi |

```bash
hermes config set plugins.entries.hexpi.settings.model sonnet
hermes config set plugins.entries.hexpi.settings.thinking high
hermes config set plugins.entries.hexpi.settings.home /data/hexpi-pi
hermes config get plugins.entries.hexpi
```

## Usage

Target flow, once milestone 2 lands:

```
> delegate this refactor to hexpi
```

Hermes routes the delegate task to the `hexpi` backend, starts Pi in RPC mode inside the project directory,
streams Pi's progress back as subagent progress, and returns Pi's result — summary plus the diff it left in
the tree.

## How it works

Four moving parts, each one a research question until it is proven:

1. **The route.** A delegation provider answers "which way does this task go" and returns the `hexpi` route, so
   the settings pane offers `hexpi` next to the built-in modes.
2. **The child.** Pi is started as a long-lived subprocess in `--mode rpc` (JSONL on stdin/stdout): one prompt
   in, session events out, `agent_settled` as the completion signal.
3. **The home.** `PI_CODING_AGENT_DIR` points at the plugin's own directory, so `hexpi` has its own
   `settings.json`, sessions and packages while `~/.pi` keeps the user's.
4. **The knowledge.** Hermes skills are directories of `SKILL.md` — the same shape Pi discovers under
   `~/.agents/skills/`; Hermes memory reaches Pi through the same seam, exact shape to be decided.

Deliberately **not** in scope: vendoring or forking Pi, writing into the user's `~/.pi`, running Pi on another
machine (that is a transport problem, not a plugin's), and re-implementing ACP.

## Roadmap

Milestones are ordered; each one is shippable on its own.

| # | Milestone | Ships | Open question |
|---|---|---|---|
| 0 | Repository | README, `AGENTS.md`, MIT, this roadmap | — |
| 1 | Plugin skeleton | `plugin.yaml`, `register(ctx)`, `config_schema`, `hermes plugins validate` and `doctor --ci` green | Which manifest capabilities does the delegation seam need to declare? |
| 2 | Pi runtime | Resolve `pi` from `PATH` or install it; isolated `PI_CODING_AGENT_DIR`; `hermes hexpi doctor` reporting version, home, provider | Which install path is authoritative — the shell installer or npm? Both must be supported; which one is default? |
| 3 | Pi as the subagent | RPC subprocess: prompt → events → result; cancellation, timeouts, exit codes, the diff left in the tree | Does the delegation backend alone make Pi the worker, or does the child have to be a profile whose route reaches Pi? |
| 4 | Profile description | `hexpi` appears as its own subagent with a coding description and its own route in desktop settings and CLI; ephemeral, no state kept | How much of the route vocabulary (model, provider, effort) can be passed through without Hermes overriding it? |
| 5 | Model and effort | `provider`, `model`, `thinking` mapped onto `--provider`, `--model`, `--thinking`; credentials handed to Pi per run | Where do Pi's env-var credentials come from — Hermes' provider config, `.env`, or a per-run injection? |
| 6 | Forced codemode | `codemode: true` → `--tools +codemode` on every run, independently of Pi's own `settings.json` | Do `--tools` and the isolated `defaultTools` agree, or does one silently win? |
| 7 | Hermes skills | Hermes skills visible to Pi (symlink or configured skill location); only enabled skills exposed | Pi's skill frontmatter is the Agent Skills spec; Hermes skills carry extra metadata — does Pi warn, skip or accept? |
| 8 | Hermes memory | Memory providers reachable from Pi; recalled context injected without a second implementation | MCP server, injected context document, or a pre-run hook — which one survives Pi's session model? |
| 9 | Hardening | Hermetic tests (no network, no live Pi), docs, error paths, uninstall that removes the plugin's home | — |

Research notes for these questions and the implementation plans live in the vault, not in this repository.

## Development

```
plugin/hexpi/            the plugin: plugin.yaml, __init__.py with register(ctx), provider, tests
docs/                   architecture and stack decisions, once there is something to describe
```

The plugin is Python — the standard library only — because the Hermes plugin API is Python and a second
runtime would buy nothing. Tests are plain asserts run by a script, with no framework and no network:
a test that needs a real `pi` binary or a real provider is not a test.

```bash
git clone <repo> hexpi && cd hexpi
python3 tests/selfcheck.py        # once milestone 1 lands
```

## Contributing

- One milestone per change set; keep `hermes plugins validate` and the self-check green.
- No new dependency without a reason written in `docs/stack.md`.
- Nothing in tracked files may name a host, a domain, a container or a path on someone's machine — use
  placeholders (`<host>`, `$HERMES_HOME`, `REPLACE_ME`).
- `AGENTS.md` holds the rules that apply to every agent working here; read it first.
- Open an issue for a research question from the roadmap before writing code for it.

## License

MIT — see [LICENSE](LICENSE).
