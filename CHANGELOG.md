# Changelog

Notable changes per plugin. Claude Code installs track commits directly
(no version pinning), so this file is for humans; tag a release when you
want a `.skill` artifact for claude.ai.

## Unreleased

### quality-gate

- New plugin. Sets up [qlty](https://qlty.sh) as a working quality gate — the open-source
  half of what SonarQube used to provide — through six reviewable phases: `assess`,
  `propose`, `apply`, `baseline`, `enforce`, `status`.
  The gap it fills is not `qlty init`, which already exists and takes ten seconds. What
  that produces is derived from file extensions: every detectable linter on, every
  threshold at stock, no opinion about any of it. On a codebase with history that lands
  as hundreds of findings nobody triages and a gate everyone learns to route around.
  The judgment calls are the work — which of the 70+ plugins earn their noise here, how
  qlty adopts the linters the repo already configures instead of fighting them, which
  smells and thresholds are relevant to this code, and what blocks a merge versus what
  merely reports. So the output is not just `.qlty/qlty.toml` but `docs/quality/policy.md`,
  which says what the gate enforces and why, and is the thing `status` re-reads later.
- Two reference files carry the advice the phases apply. `choosing-checks.md` orders
  checks into four tiers by value per unit of noise (formatters, security scanners,
  correctness linters, maintainability smells), gives each qlty smell its default and the
  case for moving it, and is explicit about what not to gate on — raw LOC, total issue
  count on a legacy repo, an absolute coverage percentage. `plugin-catalog.md` is the
  per-stack lookup table, including the pairs that should never both be enabled
  (`biome` with `prettier` + `eslint`, `ruff` with `flake8`, `rubocop` with `standardrb`).
- Clean-as-you-code is the default posture: gate changed files against the merge base,
  leave existing debt visible but non-blocking. Full `--all` enforcement is offered as an
  explicit upgrade once the diff gate is holding, not as the starting point — a gate that
  is red the day it is switched on teaches the team to ignore it, and that lesson is hard
  to unteach.
- Enforcement covers the three surfaces qlty itself recommends: a blocking CI job, git
  hooks (integrating with an existing `pre-commit`/husky/lefthook setup rather than
  overwriting `.git/hooks/`), and a block appended to `AGENTS.md`/`CLAUDE.md`. qlty ships
  no MCP server by design — its documented agent integration is the shell command plus the
  exit code — so that block is the whole wiring.
- `scripts/qlty_advisor.py` (standard library only, like the spec-workflow scripts) backs
  two phases. `detect` profiles a repo: languages by file and line count, tools declared in
  `pyproject.toml`/`package.json`/dotfiles, test layout, CI provider, hook runner, monorepo
  sub-projects. `verify` reads an existing `qlty.toml` and reports what is valid but wrong
  here — a plugin enabled for a language that isn't present, a linter the repo already
  configures being shadowed instead of adopted, patterns matching nothing, and a `[[triage]]`
  block that silences issues with no comment saying why. That last one exists because an
  unexplained suppression is indistinguishable from hiding a problem.
- `tests/run_checks.py` gained a section 10 covering all of the above against fixture
  repositories, plus the four shipped templates. Twelve deliberate breakages confirm the
  checks bite.
- Verified end to end against **qlty 0.643.0**: every command line the skill emits was
  executed against a real repository, and the phases were corrected where the CLI
  disagreed with the documentation. The findings worth knowing:
  `qlty githooks install` **overwrites `.git/hooks/pre-commit` and `pre-push` with no
  warning and no backup**, so `enforce` now checks and backs up first; the commit hook it
  installs only formats (`qlty fmt`) while the push hook is the one that blocks;
  `qlty smells` and `qlty metrics` always exit 0 and cannot gate; `qlty plugins list` requires
  an already-initialised repo, so `propose` uses `qlty init --dry-run` instead; `qlty init`
  writes a whole `.qlty/` tree with cache symlinks rather than just a config file, still
  samples every plugin under `--no`, and picks per-language plugin variants
  (`radarlint-python`) plus a lint-only `ruff`.
- Walked the six phases end to end against a real project (a ~7,500-line Python scraper
  and translation pipeline) and corrected what the walkthrough disproved. The important
  one: **a plugin's `mode` does not control whether it blocks.** `block`, `comment` and
  `monitor` produce byte-identical CLI behaviour and the same exit code — they are Qlty
  Cloud presentation semantics. What decides the gate is `--fail-level` (global, one bar
  for the whole run) plus `--filter` (which plugins run at all), so "block on security,
  report on the Sonar rules" is two commands rather than one config. Only
  `mode = "disabled"` does anything locally. This invalidated the mode column in both
  templates, the tier table in `propose`, and the tier advice in `choosing-checks`, all of
  which now describe the real model in a new **What actually controls the gate** section.
- Also corrected from that walkthrough: maintainability smells never reach `qlty check`
  at any setting, so nothing in that tier can fail a build; `--upstream origin/main` exits
  **99**, not 1, on a repo without that ref, so the templates derive the base ref instead
  of hardcoding it; per-smell `mode` is silently dropped and `enabled = false` is the only
  spelling that works — with `qlty config validate` still exiting 0 on the warning, so
  `apply`'s gate now demands zero warning lines rather than a zero exit; `test_patterns`
  does not stop linters running on tests, which is how one repo got 141 of its 178
  findings from `bandit`'s `B101` firing on pytest assertions; and `--summary`/`--quiet`
  cannot produce the per-plugin and per-check counts the phases ask for, so the
  measurement commands use `--json`.
- `qlty_advisor.py` gained the checks that would have caught the above: an unsupported key
  inside a `[smells.*]` block is an error, with the `mode` case naming `enabled = false`
  as the fix. `detect` now finds `pyright`/`basedpyright` (recording that qlty ships no
  plugin for them, so `propose` says "leave alone" instead of proposing `mypy` alongside),
  and reports a tool that runs with no config at all — a `.ruff_cache/` with no
  `[tool.ruff]` is an existing linter, not an absent one.

### spec-workflow
- The plugin now installs under [Oh My Pi](https://github.com/can1357/oh-my-pi) as well as
  Claude Code. It already loaded there through omp's Claude-compatibility fallback; what's
  new is a root `plugin.json` declaring [Agent Plugins 1.0.0](https://agent-plugins.org), so
  the skill goes through the portable-standard loader instead — and works in any client that
  implements the standard, not just omp. The Claude manifest at `.claude-plugin/plugin.json`
  is untouched and still the one Claude Code reads; commands keep loading from the Claude
  side, since that surface isn't part of the standard.
  Opting in has a sharp edge worth knowing about: under the standard a `SKILL.md` whose
  frontmatter carries any key outside the closed six-field set, or a description past 1024
  characters, is skipped in silence — the plugin still installs and the commands still work,
  so nothing visibly breaks. `tests/run_checks.py` now validates both manifests and every
  `SKILL.md` against the closed schemas, reports how much description headroom is left
  (currently 975 of 1024), and keeps eight broken fixtures around to prove the check bites.
- The phase commands pointed at `skills/spec-workflow/SKILL.md in this plugin`, a path that
  only resolves under one client. They name the skill instead.
- Mermaid diagrams are validated by the lint with [maid](https://github.com/probelabs/maid)
  when it is installed (`npm i -g @probelabs/maid`; `--mermaid npx` fetches it on
  demand, `--mermaid off` skips). A diagram that doesn't parse is an error with
  its file and line — previously it only surfaced as an error box on the review
  site, after review. maid's own warnings are reported as info: it reads `+` and
  `create(` inside a message label as syntax, which mermaid does not.
- Artifact headers are now a two-column `| Field | Value |` table instead of a
  block of `key: value` lines, which Markdown collapsed into one run-on
  paragraph on the review site. Same for the `Actors / Preconditions /
  Postconditions` trio under each requirement in `spec.md`. Templates, the
  worked example and the parsers moved together; the old block form is still
  read, and the lint notes (as info, never an error) which documents to convert.
- Fixed: `--tests-dir` marker discovery unioned every file under the tests
  directory, so one feature's `S-01.1` satisfied another's traceability and a
  feature with no tests at all could report clean. Both `spec_lint` and
  `spec_status` now read only the files that belong to the feature — the slug in
  the path, or a `{"tests": {"<slug>": ["<glob>"]}}` mapping in
  `.spec-lint.json` for layouts that don't name paths after it.
- Fixed: a brief set to `status: shipped` short-circuited the ladder before the
  lint and open-feedback checks, so a feature with errors, missing artifacts and
  unresolved comments reported as done. `shipped` is now evaluated after the
  blocking conditions and only holds when the mandatory artifacts exist and
  tests.md is green; otherwise the phase says which part is missing.
- New optional `wireframe` phase between refine and design: hand-drawn-style
  screens in `docs/features/<slug>/wireframes/*.html` (wired-elements from a
  CDN, one shared grayscale stylesheet, no build step), covering the UI-bearing
  main flows of an approved spec. Skipping it is always allowed.
- `spec_lint` checks screens: coverage comments, unknown scenario IDs, dead
  internal links, and main flows with no screen (silenced by `<!-- no-ui: ... -->`).
  A missing `wireframes/` folder is info, never an error.
- The review site lists screens under each feature, renders them in a sandboxed
  iframe and takes file-level comments into the same `feedback.md`; `spec_status`
  notes the screen count and suggests the phase when a spec is approved and no
  design exists.
- Fixed: the site's lint and next-step sidebar panels never rendered, because the
  path check looked for a leading slash the paths don't have.
- Initial migration into the marketplace repo: phases (status, define-app,
  explore, refine, design, test-spec, feedback, handoff, lint, site),
  traceability lint, local review site with feedback loop, worked example.
