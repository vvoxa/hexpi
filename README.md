# hexpi

**Hermes × Pi.** A Hermes plugin that makes [Pi](https://docs.pi.dev) — a terminal coding agent — a native
coding subagent of Hermes.

> **Status: pre-alpha.** Milestones 1–3 are in the tree: the plugin loads, its one tool runs Pi in RPC mode and
> returns Pi's final text, and the protocol is covered — line framing, id correlation, dialog replies,
> cancellation that reaches the process, stderr in every error. Profile wiring and the kanban path are next.

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
- [Releases](#releases)
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
- **A covered RPC session.** Framing by line, id correlation, completion by `agent_settled`, cancellation that
  kills the process, stderr kept for the error message. A dialog request never stalls a run: Pi has no
  ask-the-user tool and runs unattended, so anything that does ask is answered `cancelled`.
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

Two things have to exist first: Pi itself, and a Hermes profile to put the tool in.

```bash
npm install -g @earendil-works/pi-coding-agent    # Node.js 22.19+, or use https://pi.dev/install.sh
pi --version
pi                                                # authenticate once, configure codemode if you want it
```

### Order matters: install where the work is delegated *from*

A delegated subagent inherits its toolset list from the profile that delegated, not from the profile it runs
as (`tools/delegate_tool.py:269` computes the list before the child enters the target profile's scope). Verified
end to end: with the plugin enabled in the parent and the target profile's own list stripped to `file`, the
child still found and called `pi`; with the plugin disabled in the parent, the child had no `pi` at all.

So the plugin must be enabled in the profile you delegate *from* — normally `default`. The target profile's own
toolset list matters only where that profile runs by itself: a kanban worker (`hermes -p coder`) or a profile
opened by hand.

Narrow toolsets through `hermes tools`, never by writing `platform_toolsets` by hand. A plugin toolset is on by
default: it survives a saved list unless it is recorded in `known_plugin_toolsets.<platform>` and missing from
that list, and only `hermes tools` (the checklist, or `tools enable`/`tools disable`) writes that record.
Editing `platform_toolsets.cli` alone leaves `pi` enabled in every profile.

### Ask Hermes to set it up

Paste this into Hermes — desktop or `hermes` on the command line, the same prompt works in both:

```text
Set up the hexpi coding subagent on this machine.

1. Install the plugin into my current profile from https://github.com/vvoxa/hexpi#plugin:
   hermes plugins install https://github.com/vvoxa/hexpi#plugin
2. Create a profile named coder as a clone of this one, so it inherits providers, memory, skills and the plugin:
   hermes profile create coder --clone --no-alias
3. Narrow the clone's own tools (this is what a kanban worker or a hand-opened profile sees; a delegated child
   takes its tools from the parent instead):
   hermes -p coder tools disable web
   hermes -p coder tools disable terminal
   hermes -p coder tools list
4. Give one pi run room to finish (the executor's per-tool deadline is 420s by default), in both profiles:
   hermes -p coder config set timeouts.tools.sequential_call 3600
5. Route delegation to that profile: install the official advanced-delegation plugin and switch the backend.
6. Check it and report back verbatim: hermes plugins list, and the output of
   hermes -p coder tools list

Do not restart the gateway. Report what each command printed, including errors.
```

Without the prompt, the same steps by hand:

```bash
hermes plugins install https://github.com/vvoxa/hexpi#plugin
hermes profile create coder --clone --no-alias
hermes -p coder config set timeouts.tools.sequential_call 3600
hermes -p coder tools disable web
hermes -p coder tools disable terminal
hermes plugins install advanced-delegation
hermes config set delegation.backend profile_routes
```

Then list `coder` under `profile_routes` with a one-line description (`hermes delegation config`, or the
Subagents section of the desktop settings). For kanban, the card's assignee is `coder` — worktree isolation is
the dispatcher's job and needs nothing from this plugin.

### Make the review lane mandatory

A worker decides how its card ends, and `kanban_complete` ends it without a review. Nothing in the board
configuration forbids that, so the gate is a `pre_tool_call` hook, wired once in the **implementer** profile
(`coder`), never in the reviewing one:

```bash
hermes -p coder config set hooks.pre_tool_call '[{"matcher":"kanban_(complete|request_review)","command":"<repo>/hooks/kanban-review-gate.py","timeout":10}]'
hermes hooks test pre_tool_call --for-tool kanban_complete      # expect action: block
hermes hooks test pre_tool_call --for-tool kanban_request_review  # expect action: modify, reviewer=default
```

The hook does two things. It blocks `kanban_complete` with a message that names the way out, so a card cannot
be closed by the agent that wrote it. And when `kanban_request_review` arrives without a `reviewer`, it fills
in `default` — which reassigns the card, so the review lane spawns the profile that can actually read the diff,
run the tests and hold the memory. `kanban_block` and every other call pass through untouched.

**Wire it in exactly one profile.** A gate in the reviewing profile blocks the reviewer's own
`kanban_complete` too, and the card can then only escape through `kanban_block` — which is what a probe run
did before this was pinned down.

The gate is checked live rather than assumed: the block refusal reached a real worker's `kanban_complete`, and
`request_review` without a reviewer left `{"implementer": "default", "reviewer": "default"}` on the event and
`review` as the card's status. A hook needs consent before it fires — approve it at the terminal once, set
`hooks_auto_accept: true`, or run the gateway with `--accept-hooks`; an unapproved hook is skipped with a
warning in the log, which is the one way this gate silently does nothing.

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

The flow:

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
| 1 | Plugin skeleton ✅ | `plugin.yaml`, `register(ctx)` registering one tool in its own toolset, `config_schema`, `hermes plugins validate` and `doctor --ci` green | Answered: the toolset name resolves to the tool `pi`, and `platform_toolsets` alone never removes it — a plugin toolset stays on until `hermes tools` records it in `known_plugin_toolsets` and leaves it out |
| 2 | The `pi` tool end to end ✅ | `pi --mode rpc --no-session` in the working directory: one prompt in, final text out, error paths named | Answered: a rejected prompt comes back as `success: false` with the provider's message, which becomes the tool's error text |
| 3 | RPC hardened ✅ | Framing by LF only, id correlation, `extension_ui_request` answered `cancelled`, abort on interrupt, stderr tail in errors, process tree killed on timeout | Open: where does Pi's output get too large to return, and what is a useful truncation? |
| 4 | Profile wiring (delegation half ✅) | The documented recipe: cloned profile, `advanced-delegation` profile route, toolsets narrowed through `hermes tools`, kanban assignee | Answered: a child takes the calling profile's list — verified live, `pi` reached the child with the target profile stripped to `file`, and vanished once the plugin was disabled in the parent. Open: the kanban worker runs on its own config, untested |
| 5 | Integrations | Hermes skills and memory reachable from Pi; a separate Pi home if one is needed by then | MCP server, injected context document, or a pre-run hook — which one survives Pi's session model? |

Research notes for these questions and the implementation plans live in the vault, not in this repository.

## Development

```
plugin/plugin.yaml            the manifest: what this plugin provides
plugin/__init__.py            the plugin Hermes loads: register(ctx) and nothing else
plugin/pi_tool.py             the tool schema and its handler
plugin/pi_rpc.py              the RPC client: framing, ids, completion, cancellation
hooks/kanban-review-gate.py   the board gate: no self-approval, and the review lane is a named profile
tests/                        the specification: few tests, hermetic, named as claims
docs/architecture.md          components, the composition root, and the rules a test enforces
docs/testing.md               how we test, what we refuse to test
docs/releases.md              how a version, a changelog and a tag come out of commit messages
docs/style.md                 why these ruff rules, and which ones are deliberately off
pyproject.toml                ruff: the whole style guide, nothing to discuss in review
.gitconfig .editorconfig      settings both the repo and the editor enforce
```

The plugin lives in `plugin/`, so the repository root holds the project — README, docs, tests, CI — and the
plugin directory holds only what Hermes loads. Installing therefore names the subdirectory:
`hermes plugins install vvoxa/hexpi#plugin` (equivalently `…/tree/main/plugin`, or a catalog entry with
`subdir:`). That is the same shape the official `hermes-official-plugins` repository uses.

The root package is deliberately **not** `__init__.py` at the top: a Python package at the repository root makes
`pytest` treat the checkout as an importable module and import it while collecting, which then breaks in any
directory whose name is not a valid identifier (`hexpi-test`, `hexpi-main`). Keeping the package one level down
means the suite runs from any clone path.

`hermes plugins validate plugin` and `hermes plugins doctor plugin --ci` run against that directory.

The plugin is Python — the standard library only — because the Hermes plugin API is Python and a second
runtime would buy nothing. Tests are hermetic: `pytest` in the repository, no network, no real `pi` binary, no
provider. How many tests and what they are allowed to assert: `docs/testing.md`.

```bash
git clone https://github.com/vvoxa/hexpi && cd hexpi
git config --local include.path ../.gitconfig   # the repo's shared git settings
pip install ruff pytest
ruff check . && ruff format --check . && pytest -q    # what CI runs
```

Three rules that shape every review:

- **No comments.** A name, a type, a test or a docstring on the public API carries the reason. The build fails on
  a `#` in the plugin.
- **Ruff is the style authority.** Do not argue with it in review and do not silence it; a `# noqa` needs its
  reason on the same line. Why these rules: `docs/style.md`.
- **A module never imports a sibling module.** `__init__.py` is the composition root and the only place that
  wires them. Sizes and the rest: `docs/architecture.md`.

## Releases

Commit messages are the changelog: [Conventional Commits](https://www.conventionalcommits.org/), and
`release-please` turns them into a version bump, a `CHANGELOG.md` entry and a tag. The full route — including
what it means for an installing user and why the alternatives were rejected — is in
[docs/releases.md](docs/releases.md).

```bash
hermes plugins install vvoxa/hexpi#plugin                  # default branch
hermes plugins install vvoxa/hexpi#plugin --ref <sha>      # pinned, reproducible
```

## Contributing

- One milestone per change set; keep `hermes plugins validate plugin` and the test suite green.
- No new dependency without a reason written in `docs/stack.md`.
- Nothing in tracked files may name a host, a domain, a container or a path on someone's machine — use
  placeholders (`<host>`, `$HERMES_HOME`, `REPLACE_ME`).
- `AGENTS.md` holds the rules that apply to every agent working here; read it first.
- Open an issue for a research question from the roadmap before writing code for it.

## License

MIT — see [LICENSE](LICENSE).
