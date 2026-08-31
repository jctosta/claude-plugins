# Changelog

Notable changes per plugin. Claude Code installs track commits directly
(no version pinning), so this file is for humans; tag a release when you
want a `.skill` artifact for claude.ai.

## Unreleased

### spec-workflow
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
