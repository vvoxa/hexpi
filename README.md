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

Hermes spawns subagents through `delegate_task`, and a subagent can be a Hermes profile. A profile has its own
model, credentials, skills and instructions — which makes it the right place to put a coding agent.

`hexpi` is the thin half of that arrangement: a Hermes plugin installed into a profile, giving it **one tool**,
`pi`, which runs the Pi coding agent in the current working directory and returns what Pi did. The profile is
the subagent; Pi is how it writes code. Any profile with `hexpi` in it — whether reached through delegation,
through the kanban dispatcher, or opened directly — codes with Pi.

Everything Pi needs is configured from Hermes: provider, model, reasoning effort, codemode, the Pi home
directory. Pi itself is never configured by hand, and the user's own `~/.pi` is never touched.

## Features

- **One tool, `pi`.** The profile gets a single capability; the coding is Pi's, not the profile model's.
- **Works wherever a profile works.** Delegation by profile route, a kanban assignee, or a profile opened by
  hand — the same tool, the same isolated Pi home.
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

- Hermes Agent 0.23.0 or newer (plugin API)
- Python 3.11+ (the Hermes runtime; the plugin uses the standard library only)
- Network access on first run if Pi has to be installed
- A provider credential for the model Pi will use — held by Hermes, passed to Pi per run

## Installation

Not yet installable — the plugin skeleton lands in milestone 1. Target flow, on the profile that should
code with Pi:

```bash
hermes -p <profile> plugins install <owner>/hexpi
hermes plugins validate hexpi
hermes config set platform_toolsets.cli '[hexpi, file, skills]'
```

And, once, on the profile doing the delegating: the official `advanced-delegation` plugin, mode
`profile_routes`, listing that profile. For kanban, the card's assignee is the profile name.

## Configuration

Settings live under `plugins.entries.hexpi.settings` — the same tree the desktop settings pane renders and
`hermes config set` writes.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `description` | str | `coding` | What this profile's `pi` tool is for, as the settings pane shows it |
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
> delegate this refactor to the coder profile
```

Hermes runs the delegate task as that profile; the profile calls its one tool, `pi`, which starts Pi in RPC
mode inside the working directory, streams its work into the tool result, and returns what Pi did — summary
plus the diff it left in the tree. The same happens when a kanban card names the profile as its assignee.

## How it works

Four moving parts:

1. **The profile.** The subagent is a normal Hermes profile — its model, credentials, skills and instructions.
   Reachable by delegation (profile route), by kanban assignee, or by hand.
2. **The tool.** `hexpi` registers exactly one tool, `pi`, in its own toolset. The profile's model decides to
   call it; Pi decides how to code.
3. **The process.** Pi runs as a subprocess in `--mode rpc` (JSONL on stdin/stdout): one prompt in, session
   events out, `agent_settled` as the completion signal.
4. **The home.** `PI_CODING_AGENT_DIR` points at the plugin's own directory, so `hexpi` has its own
   `settings.json`, sessions and packages while `~/.pi` keeps the user's.

Deliberately **not** in scope: vendoring or forking Pi, writing into the user's `~/.pi`, running Pi on another
machine (that is a transport problem, not a plugin's), and re-implementing ACP.

### Design decisions

| Decision | Reason |
|---|---|
| Pi is driven in **RPC mode** (`pi --mode rpc`) | JSONL records with ids, a real completion signal (`agent_settled`), runtime model/effort switching, cancellation that reaches the process |
| Pi runs with its **own** `PI_CODING_AGENT_DIR` | the user's `~/.pi` stays theirs; sessions and packages do not mix |
| Settings reach Pi as **arguments and files in that home** | no `pi auth login`, no editing Pi's settings by hand |
| The plugin is **Python, standard library only** | the Hermes plugin API is Python; a second runtime buys nothing |
| No core patch | the subagent is a stock Hermes profile; hexpi only adds a tool, so nothing in Hermes has to change |
| No delegation backend in this plugin | routing a subagent to a profile is `advanced-delegation`'s `profile_routes` mode; duplicating it would put two owners on one decision |

Cancel is `abort` and waits for the session to go idle; `clear_queue` returns the messages an abort displaced.

## Roadmap

Milestones are ordered; each one is shippable on its own.

| # | Milestone | Ships | Open question |
|---|---|---|---|
| 0 | Repository | README, `AGENTS.md`, MIT, this roadmap | — |
| 1 | Plugin skeleton | `plugin.yaml`, `register(ctx)` registering one tool in its own toolset, `config_schema`, `hermes plugins validate` and `doctor --ci` green | Does a plugin toolset survive `platform_toolsets` narrowing in a profile clone? |
| 2 | Pi runtime | Resolve `pi` from `PATH` or install it; isolated `PI_CODING_AGENT_DIR`; `hermes -p <profile> hexpi doctor` reporting version, home, provider | Which install path is authoritative — the shell installer or npm? Both must be supported; which one is default? |
| 3 | The `pi` tool | RPC subprocess: prompt → events → result; cancellation, timeouts, exit codes, the diff left in the tree | Can a tool call report progress while Pi works, and does a long run survive the tool timeout? |
| 4 | Profile wiring | The documented recipe: cloned profile, `advanced-delegation` profile route, `platform_toolsets` narrowed to the `pi` toolset, kanban assignee | Child toolsets come from the calling profile, not the target profile — does the tool still reach a delegated child? |
| 5 | Model and effort | `provider`, `model`, `thinking` mapped onto `--provider`, `--model`, `--thinking`; credentials handed to Pi per run | Where do Pi's env-var credentials come from — Hermes' provider config, `.env`, or a per-run injection? |
| 6 | Forced codemode | `codemode: true` → `--tools +codemode` on every run, independently of Pi's own `settings.json` | Do `--tools` and the isolated `defaultTools` agree, or does one silently win? |
| 7 | Hermes skills | Hermes skills visible to Pi (symlink or configured skill location); only enabled skills exposed | Pi's skill frontmatter is the Agent Skills spec; Hermes skills carry extra metadata — does Pi warn, skip or accept? |
| 8 | Hermes memory | Memory providers reachable from Pi; recalled context injected without a second implementation | MCP server, injected context document, or a pre-run hook — which one survives Pi's session model? |
| 9 | Hardening | Hermetic tests (no network, no live Pi), docs, error paths, uninstall that removes the plugin's home | — |

Research notes for these questions and the implementation plans live in the vault, not in this repository.

## Development

```
plugin/hexpi/            the plugin: plugin.yaml, __init__.py with register(ctx), the pi tool, tests
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
