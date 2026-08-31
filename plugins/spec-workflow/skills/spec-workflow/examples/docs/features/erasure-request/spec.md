# Spec: Erasure request

slug: erasure-request
status: approved
brief: ./brief.md

## Requirements

## REQ-01: Erasure request submission
The system SHALL allow an authenticated subject to submit an erasure request covering all personal data held under their identifier.

Actors: Data subject, Notifier
Preconditions: subject authenticated; no erasure Request in PENDING or IN_PROGRESS (INV-01)
Postconditions: a Request of type erasure exists in PENDING with a deadline; subject has a confirmation

### S-01.1 Main flow — request accepted
- GIVEN an authenticated subject with no pending erasure request
- WHEN the subject submits an erasure request
- THEN a Request of type erasure is created with status PENDING
- AND the Request has a deadline of 15 calendar days from submission
- AND a confirmation containing the request identifier and deadline is sent to the subject
- AND an audit event "request submitted" is recorded for the Request

### S-01.2 Alternative — duplicate request
- GIVEN a subject with an erasure Request in PENDING
- WHEN the subject submits another erasure request
- THEN the submission is rejected
- AND the rejection references the identifier of the existing Request
- AND no new Request is created

### S-01.3 Exception — confirmation delivery fails
- GIVEN a valid submission
- WHEN the confirmation cannot be delivered
- THEN the Request remains in PENDING
- AND delivery is re-attempted for up to 24 hours
- AND the delivery failure is visible to the DPO
- AND if delivery still fails after 24 hours the DPO is alerted

## REQ-02: Retention obligation exception
The system SHALL erase every personal data category except those under a retention obligation, reporting the retained categories and their legal basis.

Actors: DPO, Data subject, Notifier
Preconditions: Request in IN_PROGRESS
Postconditions: erasable categories erased; Request COMPLETED; subject has a completion notice

### S-02.1 Main flow — partial erasure with retained categories
- GIVEN a subject with fiscal records under a retention obligation and an erasure Request in IN_PROGRESS
- WHEN the DPO executes the Request
- THEN every category not under a retention obligation is erased
- AND the fiscal records are kept
- AND the Request moves to COMPLETED
- AND a completion notice listing the retained categories and their legal basis is sent to the subject
- AND an audit event "request completed" listing erased and retained categories is recorded

### S-02.2 Alternative — nothing to retain
- GIVEN a subject with no data under a retention obligation and an erasure Request in IN_PROGRESS
- WHEN the DPO executes the Request
- THEN all personal data categories are erased
- AND the completion notice states that nothing was retained

### S-02.3 Exception — erasure fails midway
- GIVEN an erasure Request in IN_PROGRESS
- WHEN erasing one category fails
- THEN the Request remains in IN_PROGRESS
- AND categories already erased stay erased
- AND the failure and the remaining categories are visible to the DPO
- AND no completion notice is sent

## Cross-cutting constraints
- X-01: Submitting the same erasure request twice within the same second produces exactly one Request (idempotent under concurrent submission).
- X-02: A submission is acknowledged to the subject within 2 seconds at p95 regardless of notifier latency.

## Data and state changes
- Entities created: Request (type erasure), Audit event
- Entities modified: Subject — personal data categories erased on completion
- Lifecycle transitions used: Request: PENDING → IN_PROGRESS (out of scope, DPO dashboard), IN_PROGRESS → COMPLETED
- Invariants relied on: INV-01, INV-02
- Invariants introduced: None

## Removed
- None
