# Phase: apply

Turn the approved policy into `.qlty/qlty.toml`, and prove the config actually runs before claiming it works.

## Inputs

An approved **Policy** section in `docs/quality/policy.md`, and qlty on PATH. If the policy has not been reviewed, go back — this phase writes into the user's repository.

## Method

1. **Never run a bare `qlty init`.** It is interactive, writes `.qlty/qlty.toml` immediately, and offers to sample every plugin it enables. Use it only for reconnaissance:

   ```
   qlty init --dry-run
   ```

   That prints the config it *would* generate without saving. Read it for two things: the exact plugin names it picked, and any plugin it found that the policy never considered. A surprise there means `assess` missed something — say so rather than silently adopting it.

2. **Write the config yourself**, starting from `assets/templates/qlty.toml`. Structure, in order: `config_version`, `exclude_patterns`, `test_patterns`, `[[source]]`, `[[plugin]]` blocks, `[smells.*]` blocks, `[language.*.smells]` overrides, `[[exclude]]`, `[[triage]]`.

   Carry the reasons across as comments. The policy explains the config at length; the config should carry enough of it that someone reading `qlty.toml` alone is not mystified:

   ```toml
   # Python is the whole product surface; ruff replaces flake8+isort, which we removed.
   [[plugin]]
   name = "ruff"
   config_files = ["pyproject.toml"]
   ```

3. **Adopt existing configs rather than shadowing them.** For every plugin the policy marked "adopt", set `config_files` to the repo's own file. If the team wants the config files out of the repo root, `.qlty/configs/` is where qlty looks — move them there in the same change, and update whatever else references them.

4. **Monorepos.** One `[[plugin]]` block per sub-project that needs different treatment, each with its own `prefix`. Do not flatten a monorepo into one global config and then paper over it with `[[exclude]]` blocks.

5. **Validate the syntax before running anything:**

   ```
   qlty config validate
   python scripts/qlty_advisor.py verify <path>
   ```

   `qlty config validate` catches schema errors. `verify` catches the things that are valid but wrong here: a plugin enabled for a language that is not present, a tool configured twice, patterns matching nothing.

6. **Prove the plugins actually run.** This is the step that catches a plugin whose runtime will not install or whose version pin does not exist:

   ```
   qlty check --all --no-fail --summary
   ```

   `--no-fail` makes this diagnostic rather than a gate; findings are expected and are `baseline`'s problem, not this phase's. **Warn the user first** — the first run downloads and installs every tool qlty drives and can take several minutes. Run it in the background so the session continues.

   A plugin that errors is not configured. Fix the version, drop the plugin, or record it as blocked; do not leave a plugin in the config that cannot execute.

7. Note the qlty version in the policy header table — thresholds and plugin defaults move between releases.

## Gate

- [ ] `.qlty/qlty.toml` matches the approved policy — every enabled plugin, every threshold, every exclusion
- [ ] Reasons carried across as comments, at least for anything non-obvious
- [ ] Every "adopt" plugin has `config_files` pointing at the repo's own file
- [ ] `qlty config validate` is clean
- [ ] `qlty_advisor.py verify` reports no errors, and every warning is either fixed or explained
- [ ] `qlty check --all --no-fail` completed and every enabled plugin ran without a runtime error
- [ ] Nothing was written outside `.qlty/` (and any config files the policy said to move)
- [ ] `status: applied`, `qlty` version recorded

Then stop. Summarize: what was written, which plugins ran, how many findings came back (the number only — interpreting it is `baseline`'s job), and anything the policy asked for that could not be configured.
