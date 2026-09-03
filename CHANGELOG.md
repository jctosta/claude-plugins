# Changelog

Notable changes per plugin. Claude Code installs track commits directly
(no version pinning), so this file is for humans; tag a release when you
want a `.skill` artifact for claude.ai.

## Unreleased

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
