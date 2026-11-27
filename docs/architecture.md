# Architecture

The plugin is small on purpose, but the shape is fixed now so it does not decay into one file that does
everything.

## Components and the composition root

```
__init__.py        composition root — the only place that knows every other module
pi_tool.py         the tool as Hermes sees it: schema + handler, no protocol knowledge
pi_rpc.py          the RPC client: spawn, framing, ids, completion, cancellation
pi_home.py         where Pi's home is (later milestone; not needed by the MVP)
```

`__init__.py` builds the graph:

```
register(ctx) → handler = pi_tool.handler(rpc=pi_rpc.client(config))  → ctx.register_tool(...)
```

**A module never imports another module of this plugin.** It receives what it needs as an argument or a
constructor parameter. `pi_rpc` knows nothing about Hermes; `pi_tool` knows nothing about pipes. Only
`__init__.py` imports both, and it holds no logic beyond wiring.

Why this and not "just three files with imports": the seam between "what Hermes calls" and "how Pi is driven"
is the only part of this plugin that changes when either side moves. Keeping the import graph star-shaped
means that seam is visible in one file instead of hidden in a call chain.

## Rules, and where each one is enforced

| Rule | Enforced by |
|---|---|
| only `__init__.py` imports sibling modules | `tests/test_architecture.py`: import graph check |
| a file stays under 200 lines, a function under 40 | same test, AST sizes |
| no `#` comments anywhere in the plugin | same test, `tokenize` scan |
| public functions carry a docstring saying what they return on failure | `docs/style.md` + review |
| every tool handler returns a `str` and never raises | `pi_tool` docstring + the handler's own `except` |
| settings are read through `ctx.get_config`, never `os.environ` | review; `S` rules catch the ambient read |

The three mechanical ones are tests, not prose, because a rule that only lives in a document is a rule the next
agent breaks with a clear conscience.

## SOLID, translated

The acronym is not the rule; these are:

- **One reason to change per module.** `pi_rpc` changes when Pi's protocol changes. `pi_tool` changes when
  Hermes' tool API changes. They do not change together.
- **Depend on the shape you use, not on the object.** `pi_tool` takes a callable `rpc(prompt, cwd) -> Result`,
  so a test passes a fake without importing `pi_rpc` at all.
- **No god object.** If a module needs a fourth collaborator, it is two modules.
- **Depth over width.** A module exposes one entry point and hides the rest behind it. Three small functions
  in a chain are better than one 300-line function with four levels of `if`.
- **Nothing talks sideways.** Composition is `__init__.py`'s whole job; that is also what keeps modules
  independent and testable one at a time.

## What "public API" means here

A module's public API is what `__init__.py` calls and what a test calls. Exactly that gets a docstring, and
only that. An internal helper needs a name that says what it does instead — if it needs a sentence of prose to
be understood, the name is wrong.

Comments are not allowed at all: `#` is for the interpreter, not for the reader. What the code cannot say with
names, types and tests goes in a docstring or in `docs/`.

## Sizes, concretely

- a module: one component, under 200 lines;
- a function: under 40 lines, one level of abstraction;
- a handler: parses arguments, calls one collaborator, renders the result — no loops over protocol records;
- if a function needs a `# ---- section ----` banner, it is two functions.

## Growth path

When the plugin outgrows four modules, they move into a package (`hexpi/…`) and the root keeps `plugin.yaml`,
`__init__.py` and nothing else. The import rule does not change; only the paths do.
