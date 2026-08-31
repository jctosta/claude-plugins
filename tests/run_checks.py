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

print()
if failures:
    print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
