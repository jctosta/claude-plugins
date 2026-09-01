# Product: Lacre (example excerpt)

| Field | Value |
|---|---|
| status | active |
| updated | 2026-08-31 |

## Vision
A DPO at a Brazilian SMB can receive, track and fulfil any LGPD data-subject request within the legal deadline without asking engineering for help.

## Actors
- **Data subject** — a person whose data the business holds; wants to exercise LGPD rights with minimal friction.
- **DPO** — the encarregado; wants every request tracked, deadlines visible, and evidence of fulfilment.
- **Notifier** — external email/SMS provider; delivers confirmations and completion notices.

## Jobs to be done
1. Data subject can submit an access, correction or erasure request and know the deadline.
2. DPO can see every open request with its deadline and status.
3. DPO can prove, per request, what was done and when.

## Non-goals
- Consent management — different product surface (→ future)
- Legal advice or automated DPIA (→ never)

## Constraints
- Stack: Python (FastAPI), Postgres, self-hosted
- Compliance: LGPD — deadlines and audit trail are legal obligations, not features
- Integrations: transactional email provider
- Operational: single developer, v1 in 6 weeks

## Capability map
| Capability | Responsibility | Status |
|---|---|---|
| subject-requests | Intake and lifecycle of data-subject requests | planned |
| audit | Immutable record of every action on personal data | planned |
| notifications | Outbound messages to subjects and DPO | planned |

## Feature roadmap
| Slug | Capability | Rigor | Priority | Release |
|---|---|---|---|---|
| erasure-request | subject-requests | full | P1 | v1 |
| request-dashboard | subject-requests | lite | P1 | v1 |
| audit-log | audit | full | P2 | v1 |

## v1 demo scenario
A data subject submits an erasure request from the portal and receives a confirmation with the deadline. The DPO sees it on the dashboard, executes it, and the subject receives a completion notice listing what was retained under legal obligation. The audit log shows both events.

## Assumptions
- Subjects authenticate via the business's existing customer login (assumed)
