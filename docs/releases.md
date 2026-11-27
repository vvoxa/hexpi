# Releases

One route, no branching model. A release is a tag, a changelog entry and a version bump — all produced from
commit messages, none written by hand.

## 1. Commit messages decide the changelog

[Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <subject>`, imperative, lower
case after the colon.

| Type | In the changelog | Version bump |
|---|---|---|
| `feat` | Features | minor |
| `fix` | Bug fixes | patch |
| `refactor`, `perf` | Refactoring / Performance | patch (perf) or none |
| `docs`, `test`, `chore`, `ci` | omitted | none |
| `feat!` or `BREAKING CHANGE:` in the body | Breaking changes | major |

A commit that is not conventional is simply not in the changelog. That is the whole mechanism: the discipline
lives in the commit, not in a release meeting.

## 2. `release-please` turns them into a release PR

> Status: the workflow below lands in milestone 1, together with `plugin.yaml` — it has nothing to bump before
> that file exists. The rule it depends on (conventional commits) applies from now on.

`.github/workflows/release.yml` runs
[`googleapis/release-please-action`](https://github.com/googleapis/release-please) on every push to `main`.
It opens (and keeps updating) one pull request per unreleased change:

- bumps `version` in the places listed in `release-please-config.json` — `plugin.yaml` is the one that exists
  today; a `pyproject.toml` joins the list if and when the plugin is packaged, so the manifest and the package
  can never disagree;
- writes the next `CHANGELOG.md` section from the commit messages since the last tag.

Merging that PR is the release. The action then creates the tag `vX.Y.Z` and a GitHub release whose body is the
new changelog section. Nobody tags by hand, so nobody tags the wrong commit.

## 3. What a release means for a user

The plugin installs from this repository, so the tag *is* the distribution:

```bash
hermes plugins install vvoxa/hexpi#plugin          # default branch
hermes plugins install vvoxa/hexpi#plugin --ref <40-char-sha>   # pinned, reproducible
```

`hermes plugins install --ref` takes an immutable commit, which is why the README's install line and every
release note quote a tag and not a branch.

## 4. Versioning

Semantic versioning on the *plugin's* surface, which is: the tool name, its argument schema, the settings keys
and the manifest fields Hermes reads.

- `0.x` — the MVP. Breaking changes allowed in a minor, still recorded as `BREAKING CHANGE` so the changelog
  says so.
- `1.0.0` — once the `pi` tool's schema and settings are the ones we intend to keep.
- A `requires_hermes` bump is its own line in the changelog: it is the one field that can break an install on a
  Hermes the user has not upgraded.

## 5. Gates before the release PR is mergeable

```bash
hermes plugins validate plugin
hermes plugins doctor plugin --ci
pytest -q
```

All three run in CI on every PR; the release PR is merged only when they are green on it. No manual changelog
edits — if a changelog line is wrong, the commit message is wrong, and the fix is to squash the commit, not to
patch the generated file.

## Why not the alternatives

| Rejected | Reason |
|---|---|
| hand-written `CHANGELOG.md` + manual tag | the changelog drifts from the code within two releases, and a manual tag eventually lands on the wrong commit |
| `python-semantic-release` | does the same job but needs the packaging story we do not have yet (nothing is published to PyPI) |
| a `version` bump in every PR | turns a release into a merge-conflict per PR and tells nobody what changed |
| date-based versions | says nothing about compatibility, which is the only thing an installing user cares about |
