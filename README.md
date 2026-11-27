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

Pi keeps its own configuration — model, provider, credentials, codemode — so there is nothing to duplicate
here. The plugin's job is the call: start Pi, hand it one prompt, follow the protocol to the end, return what
it did, and leave no process or session behind.

## Features

- **One tool, `pi`.** The profile gets a single capability; the coding is Pi's, not the profile model's.
- **Works wherever a profile works.** Delegation by profile route, a kanban assignee, or a profile opened by
  hand — the same tool, the same behaviour.
- **A covered RPC session.** Framing, id correlation, completion by `agent_settled`, dialog requests answered,
  cancellation that kills the process, stderr kept for the error message.
- **Pi as it is.** codemode, provider, model and credentials stay Pi's own settings; the plugin adds nothing
  Pi would have to be reconfigured for.
- **No litter.** Runs carry `--no-session`, so the user's Pi history stays theirs.
- **Tool-native.** One call, one result — usable from a chat, a delegated profile, a kanban worker or cron.
- **Both surfaces.** The tool is registered the same way for the desktop app and for `hermes` on the command
  line.

## Requirements

- Hermes Agent 0.23.0 or newer (plugin API)
- Python 3.11+ (the Hermes runtime; the plugin uses the standard library only)
- Pi on `PATH` — `npm install -g @earendil-works/pi-coding-agent` (Node.js 22.19+), or the installer from
  <https://pi.dev>
- Pi authenticated and configured the way you want it to run — `hexpi` does not do that for you

## Installation

Not yet installable — the plugin skeleton lands in milestone 1. Target flow, on the profile that should
code with Pi:

```bash
hermes -p <profile> plugins install <owner>/hexpi
hermes plugins validate hexpi
hermes -p <profile> config set platform_toolsets.cli '[hexpi, file, skills]'
hermes -p <profile> config set timeouts.tools.sequential_call 3600
```

And, once, on the profile doing the delegating: the official `advanced-delegation` plugin, mode
`profile_routes`, listing that profile. For kanban, the card's assignee is the profile name.

## Configuration

Pi configures itself. The MVP passes nothing to it that Pi could read from its own settings:
`codemode` is Pi's `defaultTools`, provider and model are Pi's own config, credentials are Pi's own auth.

The plugin has one setting, and it is about the tool call rather than Pi:

| Key | Type | Default | Meaning |
|---|---|---|---|
| `timeout_s` | int | `3600` | How long one `pi` call may run before the process tree is killed |

```bash
hermes config set plugins.entries.hexpi.settings.timeout_s 3600
hermes config get plugins.entries.hexpi
```

Hermes' own per-tool deadline (`timeouts.tools.sequential_call`, 420 s by default) sits below this one; raise
it on the profile that runs Pi, or a long coding task is cut off by the executor's timer:

```bash
hermes config set timeouts.tools.sequential_call 3600
hermes gateway restart
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
3. **The process.** Pi runs as a subprocess in `--mode rpc --no-session` (JSONL on stdin/stdout): one prompt
   in, session events out, `agent_settled` as the completion signal. `--no-session` is what keeps the user's
   Pi home clean of our runs; nothing else about Pi's configuration is touched.

Deliberately **not** in scope: vendoring or forking Pi, writing into the user's `~/.pi`, running Pi on another
machine (that is a transport problem, not a plugin's), and re-implementing ACP.

### Design decisions

| Decision | Reason |
|---|---|
| Pi is driven in **RPC mode** (`pi --mode rpc`) | JSONL records with ids, a real completion signal (`agent_settled`), runtime model/effort switching, cancellation that reaches the process |
| MVP: **`--no-session`**, no custom Pi home | one flag keeps our runs out of the user's Pi sessions; a separate home buys nothing until `hexpi` needs its own `settings.json` |
| Pi configures **itself** (codemode, provider, model, credentials) | duplicating Pi's own settings in the plugin is a second source of truth with no benefit |
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
| 2 | The `pi` tool end to end | `pi --mode rpc --no-session` in the working directory: one prompt in, final text out, error paths named | Does `agent_settled` arrive for a prompt that does nothing, and what does a rejected prompt look like? |
| 3 | RPC hardened | Framing by LF only, id correlation, `extension_ui_request` answered `cancelled`, abort on interrupt, stderr tail in errors, process tree killed on timeout | Where does Pi's output get too large to return, and what is a useful truncation? |
| 4 | Profile wiring | The documented recipe: cloned profile, `advanced-delegation` profile route, `platform_toolsets` narrowed to the `pi` toolset, kanban assignee | Child toolsets come from the calling profile, not the target profile — does the tool still reach a delegated child? |
| 5 | Integrations | Hermes skills and memory reachable from Pi; a separate Pi home if one is needed by then | MCP server, injected context document, or a pre-run hook — which one survives Pi's session model? |

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
