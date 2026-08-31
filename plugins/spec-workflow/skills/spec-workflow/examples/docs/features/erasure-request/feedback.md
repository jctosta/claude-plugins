# Feedback: erasure-request

Review comments on the artifacts in this folder. Open items are addressed in the `feedback` phase; resolved items keep their resolution line.

## F-01 [spec.md] [S-01.3] resolved
2026-08-31 · carlos
> AND delivery is re-attempted later

How many times? The subject should know when to escalate — say attempts stop after 24h and the DPO is alerted.

Resolution: S-01.3 now bounds re-attempts to 24h and alerts the DPO afterwards; T-01.3a asserts the alert; design.md test hook for S-01.3 adds the fake clock.

## F-02 [spec.md] [REQ-02] resolved
2026-08-31 · carlos

Also cover correction requests? No — keep out of scope, just confirm in brief.
Resolution: Confirmed out of scope; brief already lists it.

## F-03 [wireframes/request-form.html] [] resolved
2026-08-31 · carlos

The subject should see the 15-day deadline before submitting, not only on the confirmation.

Resolution: request-form.html now states the 15 calendar day deadline in the intro copy (S-01.1); no spec change — the deadline was already in the THEN lines.
