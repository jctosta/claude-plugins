# Quality policy

| Field | Value |
| --- | --- |
| status | assessed |
| updated | YYYY-MM-DD |
| qlty | (version this policy was written against) |
| owner | (who to ask when the gate is wrong) |

What this project checks, what blocks a merge, and why. The configuration lives in
`.qlty/qlty.toml`; this document is the argument behind it. If a check here stops making
sense, change it here first and then change the config.

## Project profile

*Written by `assess`.*

### Languages

| Language | Files | Lines | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

### Existing tooling

| Tool | Config | Run by CI? | Disposition |
| --- | --- | --- | --- |
|  |  |  | adopt / replace / leave alone |

### Shape

- Age and size:
- Monorepo:
- Tests:
- CI:
- Existing hook runner:
- Generated / vendored / excluded:

### What hurts today

*The answer that shapes everything below. If it is "nothing in particular", say so.*

## Policy

*Written by `propose`. Approved by: (name, date)*

### Plugins

| Plugin | Tier | On? | Mode | Config source | Why |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

### Smells

| Check | Threshold | Mode | Why (if not default) |
| --- | --- | --- | --- |
|  |  |  |  |

### Exclusions

| Pattern | Kind | Covers |
| --- | --- | --- |
|  | exclude / test |  |

### The gate

| Field | Value |
| --- | --- |
| command | `qlty check --upstream origin/main --fail-level=...` |
| computed over | changed files / all files |
| adoption posture | clean as you code / full enforcement |
| tightens when |  |

### Deferred

| Check | Why not now | What would change the answer |
| --- | --- | --- |
|  |  |  |

## Baseline

*Written by `baseline`. Measured on: (date, commit)*

### Findings

| Level | Count |
| --- | --- |
| high |  |
| medium |  |
| low |  |
| fmt |  |

| Plugin | Findings | Notes |
| --- | --- | --- |
|  |  |  |

### Smells

| Check | Findings |
| --- | --- |
|  |  |

### Complexity hotspots

| File | Complexity | Last touched |
| --- | --- | --- |
|  |  |  |

### Interpretation

*Where the debt actually is: which rules dominate, how much sits in cold code, how much
was formatting. The number alone means nothing.*

### Suppressions

| What | Instrument | Why |
| --- | --- | --- |
|  | exclude_patterns / [[exclude]] / [[triage]] |  |

### Promotion path

| Check | Currently | Promotes to `block` when |
| --- | --- | --- |
|  | monitor |  |

## Enforcement

*Written by `enforce`.*

| Surface | What runs | Blocks? | Verified |
| --- | --- | --- | --- |
| CI |  |  |  |
| Git hooks |  |  |  |
| Agent instructions |  | n/a |  |

### Bypass

*How to get past the gate in an emergency, and what is expected afterwards.*

## Changes

| Date | Change | Why |
| --- | --- | --- |
|  |  |  |
