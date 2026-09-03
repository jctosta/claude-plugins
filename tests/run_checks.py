#!/usr/bin/env python3
"""CI checks for the spec-workflow plugin.

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
Exits non-zero on the first failure.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
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

print()
if failures:
    print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
