# Worked example

`docs/product/` and `docs/features/erasure-request/` show a complete rigor-full feature that passes `scripts/spec_lint.py` with zero errors and zero warnings. Read it when unsure what a finished artifact looks like at each phase, and use it as a calibration point for level of detail: the spec is the longest artifact, the brief fits on one screen, design carries all the implementation vocabulary, tests.md mirrors every THEN with an assert.

`feedback.md` shows the review loop: F-01 was left on the site, applied in the `feedback` phase (spec, tests and design hook changed together) and resolved with a note; F-02 was a question answered without an edit.

```
python scripts/spec_lint.py examples/docs/features/erasure-request --matrix
python scripts/spec_status.py examples/docs
python scripts/spec_site.py examples/docs
```
