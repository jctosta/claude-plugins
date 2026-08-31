# jctosta-plugins

Personal Claude Code plugin marketplace. One repo, several plugins; installs track this repository, so updating a plugin is `git push` here and `/plugin marketplace update` (or the background auto-update) everywhere else.

Currently shipping:

| Plugin | What it does |
|---|---|
| `spec-workflow` | Spec-first development workflow: define the product, explore → refine → design → test-spec each feature, validate spec and tests *before* code, with a traceability lint, a local review site with comment-driven feedback, and handoff to Backlog.md tasks. |

## Install (Claude Code)

```shell
/plugin marketplace add jctosta/claude-plugins
/plugin install spec-workflow@jctosta-plugins
```

Then either invoke the phase commands directly:

```shell
/spec-workflow:status
/spec-workflow:define-app
/spec-workflow:explore checkout-flow "users abandon at the payment step"
/spec-workflow:refine checkout-flow
/spec-workflow:design checkout-flow
/spec-workflow:test-spec checkout-flow
/spec-workflow:feedback checkout-flow
/spec-workflow:handoff checkout-flow
/spec-workflow:lint
/spec-workflow:site
```

…or just talk ("spec this out", "where are we", "apply the review comments") — the skill routes by intent too.

## Enable per project

Commit this to a project's `.claude/settings.json` so the marketplace registers (after folder trust) and the plugin is on by default for that repo:

```json
{
  "extraKnownMarketplaces": {
    "jctosta-plugins": {
      "source": { "source": "github", "repo": "jctosta/claude-plugins" }
    }
  },
  "enabledPlugins": {
    "spec-workflow@jctosta-plugins": true
  }
}
```

## Updating

- **Claude Code**: no version is pinned in `plugin.json` on purpose — for git sources the resolved commit SHA is the version, so every push here is an update. Users pick it up via background auto-update or `/plugin marketplace update jctosta-plugins`. If this ever becomes public-facing, switch to explicit `version` + tags and bump on every release.
- **claude.ai / mobile**: skill uploads there don't track git. Tag a release (`git tag v2026.09.01 && git push --tags`) and the release workflow attaches a `<skill>.skill` file to the GitHub Release; download it and re-upload in Settings → Capabilities.

## Repository layout

```
.claude-plugin/marketplace.json      # the catalog Claude Code reads
plugins/
  spec-workflow/
    .claude-plugin/plugin.json       # plugin manifest (no version field — see Updating)
    commands/                        # thin /spec-workflow:<phase> wrappers
    skills/spec-workflow/            # the actual skill
      SKILL.md                       # router + shared conventions
      references/                    # one file per phase, read on demand
      assets/templates/              # artifact templates
      scripts/                       # spec_lint.py, spec_status.py, spec_site.py
      examples/                      # worked example that CI keeps honest
tests/run_checks.py                  # CI entry point
.github/workflows/ci.yml             # checks on every push/PR
.github/workflows/release.yml        # .skill artifacts on tags
```

## CI

`tests/run_checks.py` (runs on every push and PR):

1. The worked example passes `spec_lint` with **0 errors, 0 warnings** — it's the calibration target the skill points agents at, so it must stay clean.
2. Six deliberately broken copies of the example each trigger the lint (wrong scenario heading, missing WHEN, implementation word in the spec, test-ID mismatch, uncovered scenario, blocking question on an approved brief).
3. `spec_status` parses the example and derives the expected phase.
4. The review site's embedded JS parses (`node --check`) and a comment round-trips through `feedback.md` (append → parse → resolve).

A second job runs `claude plugin validate .` for manifest/frontmatter schema errors.

## Adding a new plugin

1. `mkdir -p plugins/<name>/.claude-plugin plugins/<name>/skills/<name>`
2. Drop the skill folder under `skills/<name>/`, write `plugin.json` (name, description, author — omit `version`).
3. Add commands under `commands/` if the skill benefits from explicit entry points.
4. Append an entry to `.claude-plugin/marketplace.json` (`"source": "./plugins/<name>"`).
5. If it has checkable invariants, extend `tests/run_checks.py`.
6. `claude plugin validate .`, then test locally: `/plugin marketplace add ./path/to/this/repo` and `/plugin install <name>@jctosta-plugins`.

## Working on the spec-workflow skill itself

The skill is self-hosting in spirit: edit an artifact convention → update the matching template, phase reference, lint rule and the worked example together, and keep the example at 0/0. `python tests/run_checks.py` before pushing tells you if the four drifted apart.
