# Phase: enforce

Put the gate somewhere it runs without anyone remembering to run it: CI, git hooks, and the instructions your coding agents read. A policy nothing executes is a document, not a gate.

## Inputs

An approved policy and a **green baseline** — the gate command verified to exit 0 on a clean tree. Do not enforce a gate that is already failing.

## Method

Three surfaces. Wire them in this order; each is useful alone.

### 1. CI — the surface that actually blocks

Start from `assets/templates/quality-gate.yml` and adapt. The essentials, whatever the provider:

- Full history (`fetch-depth: 0`), or `--upstream` has no merge base to diff against.
- Install qlty (`curl https://qlty.sh | sh`, or the official action on GitHub).
- Cache `~/.qlty` between runs, or every build re-downloads every tool.
- Run the exact command from the policy. Not a variation of it — the same string, so CI and a developer's terminal agree.
- Let the exit code fail the job. No `|| true`.

Two jobs are usually right: the diff gate on pull requests, and a nightly or push-to-main `--all --no-fail` run that records the full picture without blocking.

For a provider without a template here, the shape is identical: checkout with history, install, run, honour the exit code.

### 2. Git hooks — fast feedback before code leaves the machine

**Check what is already there first.** The profile from `assess` lists any hook runner. Clobbering someone's `pre-commit` setup is a bad way to introduce a quality tool.

- **Nothing installed** — `qlty githooks install` is the direct route.
- **`pre-commit`, husky or lefthook already installed** — add qlty as a hook entry in *that* framework instead. It owns `.git/hooks/`; do not fight it.
- **A hand-written hook exists** — show it to the user and let them decide whether to merge or replace.

Keep hooks fast. A pre-commit hook that takes 30 seconds gets bypassed. Formatting and quick lints belong at pre-commit; anything slow belongs at pre-push or in CI. qlty's `triggers` field on a plugin controls this per plugin:

```toml
[[plugin]]
name = "trivy"
triggers = ["build"]   # too slow for a commit hook
```

Tell the user the escape hatch exists (`git commit --no-verify`) and that it is for emergencies. People find it anyway; better they know it is sanctioned and rare than discover it during an incident.

### 3. Agent instructions

qlty ships no MCP server, deliberately — its documented integration for coding agents is the shell command plus the exit code. So the wiring is a block of text in the file agents already read.

Append `assets/templates/agents-snippet.md` to the repo's `AGENTS.md`, or `CLAUDE.md`, or both — whichever exist. Adapt the commands to the policy's actual gate. If neither file exists, ask before creating one.

The block tells an agent to format and self-fix before handing work back, so the gate is not the first time anyone learns the code is wrong:

```
qlty fmt
qlty check --fix --level=low
```

Where the client supports hooks natively (Claude Code hooks, for instance), a post-edit hook running `qlty fmt` on the touched file is stronger than an instruction, because it does not depend on the model choosing to comply. Offer it; do not configure someone's client without asking.

## Method, continued

4. **Verify each surface actually fires.** Not "the file was written" — that it runs:
   - CI: push the branch and read the run, or trigger it manually.
   - Hooks: make a trivial violating change in a scratch worktree and confirm the hook catches it. Do not test hooks by committing something broken to a real branch.
   - Agent block: confirm the file contains it and the commands in it are the policy's.

5. Write the **Enforcement** section of `docs/quality/policy.md`: what runs where, what blocks, how to bypass, and who to ask when it is wrong. Set `status: enforced`.

## Gate

- [ ] CI job runs the policy's exact gate command and its exit code fails the build
- [ ] CI checks out full history and caches the qlty toolchain
- [ ] Hooks installed without displacing an existing hook runner — or integrated into it
- [ ] Hook runtime is fast enough that people will not bypass it; slow plugins moved to `build` triggers
- [ ] Agent instructions present in a file agents actually read, with the policy's commands
- [ ] Each surface verified to fire, not just to exist
- [ ] Bypass procedure documented
- [ ] `status: enforced`

Then stop. Summarize: what blocks a merge now, what runs locally, what the agents were told, and the one thing most likely to make someone want to bypass this in the first month.
