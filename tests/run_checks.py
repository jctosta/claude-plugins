#!/usr/bin/env python3
"""CI checks for the plugins in this marketplace.

Run from the repository root:  python tests/run_checks.py

Checks:
1. The worked example passes spec_lint with 0 errors and 0 warnings, and its
   wireframes stay self-contained.
2. Deliberately broken copies of the example are caught (each injected break
   produces at least one error, and the run exits non-zero).
3. spec_status runs on the example and reports the expected phase.
4. The review site's embedded JavaScript parses (node --check), it lists a
   feature's wireframes, and its backend round-trips a comment (including one
   on a wireframe screen) through feedback.md.
5. Mermaid diagrams in the example are valid, and a malformed one is reported
   as an error with its line (skipped when @probelabs/maid isn't installed).
6. Document headers are two-column tables that parse, escaped pipes included,
   with the legacy `key: value` block still readable.
7. Code markers are discovered per feature: two features sharing S-01.1 don't
   satisfy each other's traceability, and .spec-lint.json can map files to a slug.
8. A brief marked `shipped` is only accepted as terminal once the lint, the open
   feedback, the mandatory artifacts and tests.md all back it up.
9. Every plugin.json and SKILL.md conforms to the closed Agent Plugins 1.0.0
   schemas, so an Agent Plugins client (Oh My Pi) can't silently drop the skill.
10. quality-gate's advisor profiles fixture repositories correctly, its verify
   catches a qlty.toml that is invalid or inconsistent with the repo, and the
   templates it ships stay parseable and complete.
Exits non-zero on the first failure.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugins/spec-workflow/skills/spec-workflow"
SCRIPTS = SKILL / "scripts"
EXAMPLE = SKILL / "examples/docs"
FEATURE = EXAMPLE / "features/erasure-request"

sys.path.insert(0, str(SCRIPTS))
import spec_lint  # noqa: E402
import spec_status  # noqa: E402
from spec_site import (  # noqa: E402
    append_feedback,
    build_tree,
    feedback_label,
    feedback_path,
    parse_feedback,
    set_status,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def run_lint(path: Path) -> spec_lint.Report:
    forbidden = spec_lint.load_forbidden(path.parent)
    return spec_lint.lint_feature(path, None, forbidden)


def run_lint_maid(path: Path) -> spec_lint.Report:
    forbidden = spec_lint.load_forbidden(path.parent)
    return spec_lint.lint_feature(path, None, forbidden, None, spec_lint.maid_command("auto"))


print("1. worked example is clean")
rep = run_lint(FEATURE)
check("example: 0 errors", len(rep.errors) == 0, "; ".join(rep.errors))
check("example: 0 warnings", len(rep.warnings) == 0, "; ".join(rep.warnings))

WIREFRAMES = sorted((FEATURE / "wireframes").glob("*.html"))
wf_text = {w.name: w.read_text(encoding="utf-8") for w in WIREFRAMES}
check("example: wireframes present", len(WIREFRAMES) == 3, f"{len(WIREFRAMES)} screen(s)")
check("example: shared stylesheet exists", (EXAMPLE / "features/.wireframe.css").exists())
check("example: every screen declares coverage on line 1",
      all(t.splitlines()[0].startswith("<!-- covers ") for t in wf_text.values()))
check("example: every screen is self-contained (X-01)",
      all('href="../../.wireframe.css"' in t and "cdn.jsdelivr.net/npm/wired-elements" in t
          for t in wf_text.values()))

print("2. broken fixtures are caught")
BREAKS = [
    # (name, file, old, new, severity: "error" | "warning")
    ("bad scenario kind", "spec.md", "### S-02.3 Exception — erasure fails midway",
     "### S-02.3 Exceptional — erasure fails midway", "error"),
    ("missing WHEN", "spec.md", "- WHEN the subject submits another erasure request\n", "", "error"),
    ("forbidden word in spec", "spec.md", "a Request of type erasure is created with status PENDING",
     "a row is inserted in the requests table with status PENDING", "warning"),
    ("test id mismatch", "tests.md", "| S-01.2 | T-01.2a |", "| S-01.2 | T-01.3a |", "error"),
    ("uncovered scenario", "tests.md",
     "| S-02.2 | T-02.2a | integration | subject with no retained categories; request IN_PROGRESS | all categories erased; completion notice retained == [] with \"nothing retained\" text |\n", "", "error"),
    ("blocking question on approved brief", "brief.md", "| user | no |", "| user | yes |", "error"),
    ("wireframe covers unknown scenario", "wireframes/request-form.html",
     "<!-- covers S-01.1, S-01.2 -->", "<!-- covers S-05.1, S-01.2 -->", "error"),
    ("wireframe dead link", "wireframes/dpo-execution.html",
     '<a href="request-confirmation.html">Confirmation</a>',
     '<a href="request-receipt.html">Confirmation</a>', "error"),
    ("main flow with no wireframe", "wireframes/dpo-execution.html",
     "<!-- covers S-02.1, S-02.2, S-02.3, S-01.3 -->", "<!-- covers S-02.2, S-02.3, S-01.3 -->", "warning"),
]
with tempfile.TemporaryDirectory() as td:
    for name, fname, old, new, severity in BREAKS:
        broken = Path(td) / "features" / "broken"
        if broken.exists():
            shutil.rmtree(broken)
        shutil.copytree(FEATURE, broken)
        f = broken / fname
        text = f.read_text(encoding="utf-8")
        if old not in text:
            check(f"fixture '{name}' applies", False, f"pattern not found in {fname}")
            continue
        f.write_text(text.replace(old, new), encoding="utf-8")
        r = run_lint(broken)
        hits = r.errors if severity == "error" else r.warnings
        check(f"caught: {name}", len(hits) > 0, f"no {severity}s reported")

print("3. spec_status on the example")
prod, feats = spec_status.collect(EXAMPLE, None, None)
check("status: product ok", prod["product_md"] and prod["domain_md"])
check("status: one feature", len(feats) == 1)
check("status: phase is implementation", feats and feats[0].phase == "implementation",
      feats[0].phase if feats else "none")
check("status: roadmap parsed", len(prod["roadmap"]) == 3, str(len(prod["roadmap"])))

print("4. review site")
site_src = (SCRIPTS / "spec_site.py").read_text(encoding="utf-8")
html = re.search(r'PAGE = r"""(.*?)"""', site_src, re.S).group(1)
js = re.search(r"<script>\n(.*?)</script></body>", html, re.S).group(1)
node = shutil.which("node")
if node:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(js)
    r = subprocess.run([node, "--check", fh.name], capture_output=True, text=True)
    check("site JS parses", r.returncode == 0, r.stderr.strip()[:200])
else:
    print("  skip site JS parse (node not found)")

with tempfile.TemporaryDirectory() as td:
    docs = Path(td) / "docs"
    shutil.copytree(EXAMPLE, docs)
    fb = docs / "features/erasure-request/feedback.md"
    before = len(parse_feedback(fb))
    item = append_feedback(fb, "spec.md", "S-01.1", "quoted line", "ci round-trip", "ci")
    items = parse_feedback(fb)
    check("feedback: appended", len(items) == before + 1)
    check("feedback: fields survive round-trip",
          any(i["id"] == item["id"] and i["text"] == "ci round-trip" and i["anchor"] == "S-01.1" for i in items))
    check("feedback: resolve works", set_status(fb, item["id"], "resolved", "done in ci")
          and any(i["id"] == item["id"] and i["status"] == "resolved" for i in parse_feedback(fb)))

    wf_rel = "features/erasure-request/wireframes/request-form.html"
    check("wireframes: listed after tests.md",
          [f["name"] for f in build_tree(docs)["features"][0]["files"]]
          == ["brief.md", "spec.md", "design.md", "tests.md",
              "dpo-execution.html", "request-confirmation.html", "request-form.html", "feedback.md"])
    check("wireframes: comments land in the feature's feedback.md", feedback_path(docs, wf_rel) == fb)
    check("wireframes: file label keeps the folder", feedback_label(wf_rel) == "wireframes/request-form.html")
    wf_item = append_feedback(fb, feedback_label(wf_rel), "", "", "screen round-trip", "ci")
    check("wireframes: comment round-trips",
          any(i["id"] == wf_item["id"] and i["file"] == "wireframes/request-form.html" and i["anchor"] == ""
              for i in parse_feedback(fb)))
    check("wireframes: comment resolves", set_status(fb, wf_item["id"], "resolved", "edited the screen")
          and any(i["id"] == wf_item["id"] and i["status"] == "resolved" for i in parse_feedback(fb)))

print("5. mermaid diagrams are validated")
maid = spec_lint.maid_command("auto")
if not maid:
    print("  skip mermaid checks (maid not installed: npm i -g @probelabs/maid)")
else:
    check("mermaid: the example's diagrams are valid",
          not [e for e in run_lint_maid(FEATURE).errors if "mermaid" in e],
          "; ".join(e for e in run_lint_maid(FEATURE).errors if "mermaid" in e))
    check("mermaid: the example raises no maid warnings either",
          not [i for i in run_lint_maid(FEATURE).info if "mermaid " in i],
          "; ".join(i for i in run_lint_maid(FEATURE).info if "mermaid " in i))
    with tempfile.TemporaryDirectory() as td:
        broken = Path(td) / "features" / "broken"
        shutil.copytree(FEATURE, broken)
        d = broken / "design.md"
        d.write_text(d.read_text(encoding="utf-8").replace(
            "    Subject->>API: submit erasure request", "    Subject->>API submit erasure request", 1),
            encoding="utf-8")
        errs = [e for e in run_lint_maid(broken).errors if "mermaid" in e]
        check("mermaid: a malformed diagram is an error", len(errs) == 1, f"{len(errs)} error(s)")
        check("mermaid: the error carries file and line", errs and errs[0].startswith("design.md:34:"),
              errs[0] if errs else "none")

print("6. document headers are tables")
HEADERED = ["product/product.md", "product/domain.md"] + [
    f"features/erasure-request/{n}" for n in ("brief.md", "spec.md", "design.md", "tests.md")]
for rel in HEADERED:
    body = (EXAMPLE / rel).read_text(encoding="utf-8").splitlines()
    check(f"header: {rel} renders as a table", body[2:4] == ["| Field | Value |", "|---|---|"],
          " / ".join(body[2:4]))
check("header: no run-on `key: value` block survives in the example or templates",
      not [str(p) for p in sorted(list(EXAMPLE.rglob("*.md")) + list((SKILL / "assets/templates").glob("*.md")))
           if re.match(r"^\w[\w ]*?:\s*\S", (p.read_text(encoding="utf-8").splitlines() + [""])[2])],
      "still block-shaped")
check("header: the table parses", spec_lint.parse_fields((EXAMPLE / "features/erasure-request/tests.md")
                                                         .read_text(encoding="utf-8")).get("status") == "skeletons-red")
check("header: a `|` in a value survives escaping",
      spec_lint.parse_fields("# T\n\n| Field | Value |\n|---|---|\n| rigor | lite \\| full — why |\n")["rigor"]
      == "lite | full — why")
check("header: the legacy key: value block still parses",
      spec_lint.parse_fields("# T\n\nslug: legacy\nstatus: approved\n")
      == {"slug": "legacy", "status": "approved"})

print("7. markers are scoped per feature")
with tempfile.TemporaryDirectory() as td:
    feats = Path(td) / "docs/features"
    for slug in ("feature-a", "feature-b"):
        shutil.copytree(FEATURE, feats / slug)
    ids = sorted(set(re.findall(r"\bS-\d{2}\.\d+\b", (FEATURE / "spec.md").read_text(encoding="utf-8"))))
    ids += sorted(set(re.findall(r"\bT-\d{2}\.\d+[a-z]\b|\bT-X\d{2}[a-z]\b",
                                 (FEATURE / "tests.md").read_text(encoding="utf-8"))))
    tests_dir = Path(td) / "tests"
    (tests_dir / "feature_a").mkdir(parents=True)
    # every marker of both features, but in a file that belongs to feature-a only
    (tests_dir / "feature_a" / "test_flows.py").write_text(
        "\n".join(f"def test_{i.replace('-', '_').replace('.', '_')}():  # {i}\n    pass" for i in ids),
        encoding="utf-8")

    fa, fb = feats / "feature-a", feats / "feature-b"
    forbidden = spec_lint.load_forbidden(feats)
    check("scoping: only the slug's own files are read",
          [p.name for p in spec_lint.feature_test_files(tests_dir, "feature-a")] == ["test_flows.py"]
          and spec_lint.feature_test_files(tests_dir, "feature-b") == [])
    code_a = [w for w in spec_lint.lint_feature(fa, tests_dir, forbidden).warnings if w.startswith("code")]
    code_b = [w for w in spec_lint.lint_feature(fb, tests_dir, forbidden).warnings if w.startswith("code")]
    check("scoping: a feature's own markers satisfy it", code_a == [], "; ".join(code_a))
    check("scoping: they don't satisfy the other feature", len(code_b) > 0,
          "feature-a's markers silenced feature-b")
    check("scoping: spec_status counts markers per feature",
          spec_status.feature_status(fa, forbidden, tests_dir).scenarios_in_code > 0
          and spec_status.feature_status(fb, forbidden, tests_dir).scenarios_in_code == 0)

    (feats / ".spec-lint.json").write_text(json.dumps({"tests": {"feature-b": ["feature_a/*.py"]}}), encoding="utf-8")
    globs = spec_lint.load_test_map(feats).get("feature-b")
    check("scoping: .spec-lint.json can map files to a slug",
          [w for w in spec_lint.lint_feature(fb, tests_dir, forbidden, globs).warnings if w.startswith("code")] == [])

print("8. shipped is verified, not trusted")
with tempfile.TemporaryDirectory() as td:
    base = Path(td) / "features"
    forbidden = spec_lint.load_forbidden(base)

    def shipped(name: str, edit=None) -> Path:
        f = base / name
        shutil.copytree(FEATURE, f)
        b = f / "brief.md"
        b.write_text(b.read_text(encoding="utf-8").replace("| status | approved |", "| status | shipped |", 1),
                     encoding="utf-8")
        if edit:
            edit(f)
        return f

    def phase(f: Path) -> str:
        return spec_status.feature_status(f, forbidden).phase

    def break_spec(f: Path) -> None:
        s = f / "spec.md"
        s.write_text(s.read_text(encoding="utf-8").replace("- WHEN the subject submits another erasure request\n", "", 1),
                     encoding="utf-8")

    def green(f: Path) -> None:
        tm = f / "tests.md"
        tm.write_text(tm.read_text(encoding="utf-8").replace("| status | skeletons-red |", "| status | green |", 1),
                      encoding="utf-8")

    check("shipped: lint errors win", phase(shipped("with-lint-errors", break_spec)) == "blocked by lint",
          phase(base / "with-lint-errors"))
    check("shipped: open feedback wins",
          phase(shipped("with-open-feedback", lambda f: append_feedback(
              f / "feedback.md", "spec.md", "S-01.1", "quoted", "still open", "ci"))) == "in review")
    check("shipped: missing artifacts are named",
          phase(shipped("without-tests-md", lambda f: (f / "tests.md").unlink())) == "shipped — incomplete")
    check("shipped: tests.md must be terminal",
          phase(shipped("tests-not-green")) == "shipped — tests not green")
    st = spec_status.feature_status(shipped("really-shipped", green), forbidden)
    check("shipped: accepted when everything backs it up",
          st.phase == "shipped" and st.next == "nothing — feature is shipped", f"{st.phase} / {st.next}")

print("9. manifests and skills conform to Agent Plugins 1.0.0")
AGENT_PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MANIFEST_FIELDS = {"$schema", "name", "version", "description", "author",
                   "homepage", "repository", "license", "keywords", "extensions"}
AUTHOR_FIELDS = {"name", "email", "url"}
SKILL_FIELDS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
PLUGIN_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")


def parse_frontmatter(text: str) -> tuple[dict[str, object], str | None]:
    """Read SKILL.md frontmatter without a YAML dependency.

    The closed skill schema only permits top-level scalars, a list, and one
    nested `key: value` map, so a scanner covers it. Returns (fields, error).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing frontmatter"
    end = next((i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---"), None)
    if end is None:
        return {}, "unterminated frontmatter"
    fields: dict[str, object] = {}
    nested: dict[str, str] | None = None
    key: str | None = None
    for ln in lines[1:end]:
        if not ln.strip():
            continue
        if ln.lstrip().startswith("-") and key is not None:
            prior = fields.get(key)
            item = ln.lstrip()[1:].strip().strip("\"'")
            fields[key] = (prior if isinstance(prior, list) else []) + [item]
            nested = None
            continue
        top = re.match(r"^(\S[^:]*):\s?(.*)$", ln)
        if top and not ln[0].isspace():
            key, value = top.group(1), top.group(2).strip()
            if value:
                fields[key], nested = value.strip("\"'"), None
            else:
                nested = {}
                fields[key] = nested
            continue
        sub = re.match(r"^\s+(\S[^:]*):\s?(.*)$", ln)
        if sub and nested is not None:
            nested[sub.group(1)] = sub.group(2).strip().strip("\"'")
            continue
        return {}, f"cannot parse frontmatter line {ln!r}"
    return fields, None


def validate_agent_plugin_manifest(path: Path, dir_name: str) -> list[str]:
    """Violations of the closed Agent Plugins 1.0.0 manifest schema (spec 5).

    A fatally invalid manifest means no component of the plugin loads at all,
    so these are the checks standing between a typo and a dead install.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("$schema") != AGENT_PLUGIN_SCHEMA:
        return [f"$schema must be exactly {AGENT_PLUGIN_SCHEMA}, got {data.get('$schema')!r}"]
    bad = [f'unknown top-level field "{k}"' for k in data if k not in MANIFEST_FIELDS]
    name = data.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 64 or not PLUGIN_NAME_RE.match(name) \
            or "--" in name or ".." in name:
        bad.append(f"invalid plugin name {name!r}")
    elif name != dir_name:
        bad.append(f"name {name!r} does not match directory {dir_name!r}")
    for field in ("version", "description", "homepage", "repository", "license"):
        if field in data and not isinstance(data[field], str):
            bad.append(f'"{field}" must be a string')
    keywords = data.get("keywords")
    if keywords is not None and (not isinstance(keywords, list)
                                 or any(not isinstance(k, str) for k in keywords)):
        bad.append('"keywords" must be an array of strings')
    author = data.get("author")
    if author is not None and not isinstance(author, dict):
        bad.append('"author" must be an object')
    elif isinstance(author, dict):
        for k, v in author.items():
            if k not in AUTHOR_FIELDS:
                bad.append(f'unknown "author" field "{k}"')
            elif not isinstance(v, str):
                bad.append(f'"author.{k}" must be a string')
    return bad


def validate_agent_skill(skill_dir: Path) -> list[str]:
    """Violations of the closed Agent Skills frontmatter schema (Agent Plugins 7.1).

    A skill that trips any of these is skipped silently — the plugin still
    installs and the commands still work, so nothing else would notice.
    """
    fields, err = parse_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    if err:
        return [err]
    bad = [f'unexpected frontmatter field "{k}"' for k in fields if k not in SKILL_FIELDS]
    name = fields.get("name")
    if not isinstance(name, str) or not name.strip():
        bad.append('missing required "name"')
    else:
        n = unicodedata.normalize("NFKC", name.strip())
        if len(n) > 64:
            bad.append('"name" exceeds 64 characters')
        if n != n.lower():
            bad.append('"name" must be lowercase')
        if n.startswith("-") or n.endswith("-"):
            bad.append('"name" cannot start or end with a hyphen')
        if "--" in n:
            bad.append('"name" cannot contain consecutive hyphens')
        if not all(c.isalnum() or c == "-" for c in n):
            bad.append(f'invalid "name" {n!r}')
        if n != unicodedata.normalize("NFKC", skill_dir.name):
            bad.append(f'"name" {n!r} does not match directory {skill_dir.name!r}')
    desc = fields.get("description")
    if not isinstance(desc, str) or not desc.strip():
        bad.append('missing required "description"')
    elif len(desc) > 1024:
        bad.append(f'"description" is {len(desc)} characters, over the 1024 limit')
    for field in ("license", "allowed-tools", "compatibility"):
        if field in fields and not isinstance(fields[field], str):
            bad.append(f'"{field}" must be a string')
    comp = fields.get("compatibility")
    if isinstance(comp, str) and len(comp) > 500:
        bad.append('"compatibility" exceeds 500 characters')
    meta = fields.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        bad.append('"metadata" must be a map of string keys to string values')
    elif isinstance(meta, dict):
        bad += [f'"metadata.{k}" must be a string' for k, v in meta.items() if not isinstance(v, str)]
    return bad


for manifest_path in sorted(REPO.glob("plugins/*/plugin.json")):
    plugin_dir = manifest_path.parent
    violations = validate_agent_plugin_manifest(manifest_path, plugin_dir.name)
    check(f"{plugin_dir.name}: plugin.json conforms", not violations, "; ".join(violations))
    legacy_path = plugin_dir / ".claude-plugin/plugin.json"
    if legacy_path.exists():
        portable = json.loads(manifest_path.read_text(encoding="utf-8"))
        legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
        drift = [k for k in ("name", "description", "author", "license")
                 if portable.get(k) != legacy.get(k)]
        check(f"{plugin_dir.name}: both manifests agree", not drift, f"differ on {', '.join(drift)}")

for skill_md in sorted(REPO.glob("plugins/*/skills/*/SKILL.md")):
    skill_dir = skill_md.parent
    violations = validate_agent_skill(skill_dir)
    fields, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    desc = fields.get("description")
    room = f"description {len(desc)}/1024" if isinstance(desc, str) else "no description"
    check(f"{skill_dir.name}: SKILL.md conforms ({room})", not violations, "; ".join(violations))

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    good_manifest = json.loads((REPO / "plugins/spec-workflow/plugin.json").read_text(encoding="utf-8"))
    good_skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    fixture_skill = root / "spec-workflow"
    fixture_skill.mkdir()

    def caught(label: str, violations: list[str]) -> None:
        check(label, bool(violations), "no violation reported")

    def manifest_violations(mutate) -> list[str]:
        data = dict(good_manifest)
        mutate(data)
        path = root / "plugin.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return validate_agent_plugin_manifest(path, "spec-workflow")

    def skill_violations(text: str) -> list[str]:
        (fixture_skill / "SKILL.md").write_text(text, encoding="utf-8")
        return validate_agent_skill(fixture_skill)

    caught("manifest: another schema version is rejected",
           manifest_violations(lambda d: d.update({"$schema": AGENT_PLUGIN_SCHEMA.replace("1.0.0", "2.0.0")})))
    caught("manifest: an unknown top-level field is rejected",
           manifest_violations(lambda d: d.update({"skills": "./skills"})))
    caught("manifest: a name unlike the directory is rejected",
           manifest_violations(lambda d: d.update({"name": "spec-flow"})))
    caught("manifest: an unknown author field is rejected",
           manifest_violations(lambda d: d.update({"author": {"github": "jctosta"}})))
    caught("skill: an unexpected frontmatter field is rejected",
           skill_violations(good_skill.replace("metadata:\n", "version: 1.0.0\nmetadata:\n", 1)))
    caught("skill: a description over 1024 characters is rejected",
           skill_violations(good_skill.replace("description: ", "description: " + "x" * 1024, 1)))
    caught("skill: a name unlike the directory is rejected",
           skill_violations(good_skill.replace("name: spec-workflow", "name: spec-flow", 1)))
    caught("skill: an uppercase name is rejected",
           skill_violations(good_skill.replace("name: spec-workflow", "name: Spec-Workflow", 1)))

print("10. quality-gate profiles a repo and catches a bad qlty.toml")
QG_SKILL = REPO / "plugins/quality-gate/skills/quality-gate"
sys.path.insert(0, str(QG_SKILL / "scripts"))
import qlty_advisor  # noqa: E402


def tree(root: Path, files: dict[str, str]) -> Path:
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


def named(entries: list, key: str) -> set[str]:
    return {str(entry[key]) for entry in entries}


def messages(findings: list, severity: str) -> list[str]:
    return [f.message for f in findings if f.severity == severity]


PY_PROJECT = {
    "pyproject.toml": "[tool.ruff]\nline-length = 100\n\n[tool.pytest.ini_options]\ntestpaths = ['tests']\n",
    "src/app.py": "def handle(request):\n    return request\n",
    "tests/test_app.py": "def test_handle():\n    assert True\n",
    ".github/workflows/ci.yml": "name: ci\non: [push]\n",
}

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)

    found = qlty_advisor.detect(tree(base / "python-ruff", PY_PROJECT))
    check("detect: finds the language", "Python" in named(found.languages, "name"))
    check("detect: finds a tool configured in pyproject.toml",
          "ruff" in named(found.tools, "tool"), sorted(named(found.tools, "tool")))
    check("detect: maps the tool to its qlty plugin",
          any(t["tool"] == "ruff" and t["qlty_plugin"] == "ruff" for t in found.tools))
    check("detect: finds the test directory", "tests" in (found.tests.get("dirs") or []))
    check("detect: finds the CI provider", found.ci == ["github-actions"], str(found.ci))
    check("detect: reports no qlty config when there is none", found.qlty["configured"] is False)

    found = qlty_advisor.detect(tree(base / "js-monorepo", {
        "package.json": json.dumps({
            "workspaces": ["apps/*", "packages/*"],
            "devDependencies": {"eslint": "^9", "prettier": "^3", "husky": "^9"},
        }),
        "apps/web/package.json": '{"name": "web"}',
        "apps/web/src/index.ts": "export const x = 1;\n",
        "packages/ui/package.json": '{"name": "ui"}',
        "packages/ui/src/button.tsx": "export const Button = () => null;\n",
        ".husky/pre-commit": "npx lint-staged\n",
    }))
    check("detect: reads devDependencies as configured tools",
          {"eslint", "prettier", "husky"} <= named(found.tools, "tool"), sorted(named(found.tools, "tool")))
    check("detect: finds monorepo sub-projects",
          {"apps/web", "packages/ui"} <= set(found.workspaces), str(found.workspaces))
    check("detect: finds an existing hook runner",
          "husky" in found.hook_runners, str(found.hook_runners))

    found = qlty_advisor.detect(tree(base / "go-project", {
        "go.mod": "module example.com/app\n",
        "main.go": "package main\n\nfunc main() {}\n",
        ".golangci.yml": "linters:\n  enable: [govet]\n",
    }))
    check("detect: finds Go and its linter config",
          "Go" in named(found.languages, "name") and "golangci-lint" in named(found.tools, "tool"))

    found = qlty_advisor.detect(tree(base / "already-configured", {
        "src/app.py": "x = 1\n",
        ".qlty/qlty.toml": 'config_version = "0"\n\n[[source]]\nname = "default"\ndefault = true\n\n[[plugin]]\nname = "ruff"\n',
    }))
    check("detect: reads an existing qlty config",
          found.qlty["configured"] is True and found.qlty["plugins"] == ["ruff"], str(found.qlty))

    # --- verify -----------------------------------------------------------

    GOOD = (
        'config_version = "0"\n'
        'exclude_patterns = ["**/node_modules/**"]\n'
        'test_patterns = ["**/tests/**"]\n\n'
        '[[source]]\nname = "default"\ndefault = true\n\n'
        '[[plugin]]\nname = "ruff"\nconfig_files = ["pyproject.toml"]\n'
    )

    def verify_with(label: str, config: str | None) -> list:
        root = base / f"verify-{label}"
        if not root.exists():
            tree(root, PY_PROJECT)
        if config is not None:
            (root / ".qlty").mkdir(parents=True, exist_ok=True)
            (root / ".qlty/qlty.toml").write_text(config, encoding="utf-8")
        return qlty_advisor.verify(root)

    check("verify: a config that matches the repo is clean",
          messages(verify_with("good", GOOD), "error") == []
          and messages(verify_with("good", GOOD), "warning") == [],
          str(verify_with("good", GOOD)))

    def caught_by_verify(label: str, config: str, severity: str = "error") -> None:
        found = messages(verify_with(label, config), severity)
        check(f"verify: {label}", bool(found), f"no {severity} reported")

    caught_by_verify("a missing config is an error", None)
    caught_by_verify("unparseable TOML is an error", 'config_version = "0"\n[[plugin\n')
    caught_by_verify("a missing config_version is an error", GOOD.replace('config_version = "0"\n', ""))
    caught_by_verify("a wrong config_version is an error", GOOD.replace('"0"', '"1"'))
    caught_by_verify("a missing [[source]] is an error",
                     GOOD.replace('[[source]]\nname = "default"\ndefault = true\n', ""))
    caught_by_verify("a plugin with no name is an error", GOOD + '\n[[plugin]]\nversion = "1.0"\n')
    caught_by_verify("an invalid plugin mode is an error", GOOD + '\n[[plugin]]\nname = "bandit"\nmode = "warn"\n')
    caught_by_verify("an invalid smell threshold is an error",
                     GOOD + '\n[smells.function_complexity]\nthreshold = -1\n')
    caught_by_verify("an invalid triage level is an error",
                     GOOD + '\n[[triage]]\nmatch.plugins = ["ruff"]\nset.level = "critical"\n')
    caught_by_verify("a plugin for an absent language is a warning",
                     GOOD + '\n[[plugin]]\nname = "rubocop"\n', "warning")
    caught_by_verify("a plugin shadowing the repo's own config is a warning",
                     GOOD.replace('\nconfig_files = ["pyproject.toml"]', ""), "warning")
    caught_by_verify("an unknown smell is a warning",
                     GOOD + '\n[smells.long_names]\nthreshold = 4\n', "warning")
    caught_by_verify("an unexplained suppression is a warning",
                     GOOD + '\n[[triage]]\nmatch.plugins = ["ruff"]\nset.ignored = true\n', "warning")

    explained = GOOD + '\n# Fixtures hold malformed payloads on purpose.\n[[triage]]\nmatch.plugins = ["ruff"]\nset.ignored = true\n'
    check("verify: a suppression with a stated reason passes",
          messages(verify_with("explained", explained), "warning") == [],
          str(messages(verify_with("explained", explained), "warning")))

    # --- shipped templates ------------------------------------------------

    templates = QG_SKILL / "assets/templates"
    template_toml = (templates / "qlty.toml").read_text(encoding="utf-8")
    check("template: qlty.toml parses",
          qlty_advisor.load_toml(template_toml) is not None)
    check("template: qlty.toml verifies against a real repo",
          messages(verify_with("template", template_toml), "error") == [],
          str(messages(verify_with("template", template_toml), "error")))

workflow = (QG_SKILL / "assets/templates/quality-gate.yml").read_text(encoding="utf-8")
check("template: the CI workflow has a trigger, jobs and the gate command",
      "\non:" in workflow and "\njobs:" in workflow and "qlty check --upstream" in workflow)
check("template: the CI workflow checks out full history for --upstream",
      "fetch-depth: 0" in workflow)
workflow_steps = "\n".join(line for line in workflow.splitlines() if not line.lstrip().startswith("#"))
check("template: the CI workflow never swallows the exit code",
      "|| true" not in workflow_steps and "continue-on-error" not in workflow_steps)

snippet = (QG_SKILL / "assets/templates/agents-snippet.md").read_text(encoding="utf-8")
check("template: the agent snippet carries qlty's own agent commands",
      "qlty fmt" in snippet and "qlty check --fix --level=low" in snippet)

policy = (QG_SKILL / "assets/templates/policy.md").read_text(encoding="utf-8")
check("template: the policy has a section per phase",
      all(heading in policy for heading in
          ("## Project profile", "## Policy", "## Baseline", "## Enforcement")))

for phase in ("assess", "propose", "apply", "baseline", "enforce", "status"):
    reference = QG_SKILL / f"references/{phase}.md"
    command = REPO / f"plugins/quality-gate/commands/{phase}.md"
    check(f"phase {phase}: has a reference and a command",
          reference.exists() and command.exists())
    if reference.exists():
        check(f"phase {phase}: its reference ends with a gate",
              "## Gate" in reference.read_text(encoding="utf-8"))

print()
if failures:
    print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
