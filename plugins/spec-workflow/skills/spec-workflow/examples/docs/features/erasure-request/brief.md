# Brief: Erasure request

| Field | Value |
|---|---|
| slug | erasure-request |
| capability | subject-requests |
| rigor | full — personal data, external notifier, legal deadline |
| status | approved |
| source | conversation |

## Original request
> None — originated in conversation

## Problem
A data subject who wants their data erased has no way to ask for it and no way to know when it will be done, so the DPO handles it by email and misses deadlines.

## Options considered
1. **Self-service portal submission** — subject submits from the authenticated portal, system tracks it. Trade-off: needs subject authentication in place.
2. **DPO-entered requests** — subject emails, DPO types it in. Trade-off: keeps the email loop that causes missed deadlines.
3. **Do less** — a mailto link and a spreadsheet. Trade-off: no deadline tracking, no evidence.

## Direction
Option 1. The missed-deadline problem comes from the manual loop; only self-service removes it. Option 2 stays available as a fallback the DPO can use later (→ future).

## Scope
In:
- Authenticated subject submits an erasure request and gets a confirmation with the deadline
- Duplicate pending requests are rejected
- Execution respects retention obligations and reports what was retained

Out:
- DPO-entered requests on behalf of a subject — separate feature (→ future)
- Access and correction request types — same lifecycle, separate features (→ future)
- Identity verification beyond the existing login — assumed sufficient for v1 (→ future)

## Actors and entities
- Actors: Data subject, DPO, Notifier
- Entities touched: Subject, Request, Audit event
- Domain changes: None

## Related
- request-dashboard (reads the Requests this feature creates)

## Open questions
| ID | Question | Owner | Blocking |
|---|---|---|---|
| Q-01 | Is the 15-day simplified deadline acceptable, or do we track both 15 and the full-response deadline? | user | no |

## Assumptions
- Deadline is 15 calendar days from submission (assumed)
