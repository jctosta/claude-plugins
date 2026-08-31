# Test spec: Erasure request

slug: erasure-request
status: skeletons-red
spec: ./spec.md
design: ./design.md
framework: pytest
marker convention: @pytest.mark.scenario("S-NN.M") + test_TNN_Ma_<name>

## Matrix
| Scenario | Test ID | Level | Fixture / setup | Asserts |
|---|---|---|---|---|
| S-01.1 | T-01.1a | integration | authenticated subject, no open request, notifier fake | 201; request row status=PENDING; deadline = today+15; outbox row kind=confirmation with id+deadline; audit event "request submitted" |
| S-01.1 | T-01.1b | unit | submission date D | deadline(D) == D + 15 calendar days, incl. month/year rollover |
| S-01.2 | T-01.2a | integration | subject with PENDING erasure request | 409; body.existing_id == pending id; request count unchanged |
| S-01.3 | T-01.3a | integration | valid submission; notifier fake raises; run_outbox_once() | request still PENDING; outbox row failed=true, attempts=1, next_attempt set; row visible via DPO failures query; after simulated 24h the DPO alert is enqueued and re-attempts stop |
| S-02.1 | T-02.1a | integration | subject with fiscal + profile categories; request IN_PROGRESS; DPO auth | profile erased; fiscal present; status COMPLETED; outbox completion lists fiscal + basis; audit event lists erased/retained |
| S-02.1 | T-02.1b | unit | RetentionPolicy with fiscal rule | classify() returns fiscal as retained with legal basis, others erasable |
| S-02.2 | T-02.2a | integration | subject with no retained categories; request IN_PROGRESS | all categories erased; completion notice retained == [] with "nothing retained" text |
| S-02.3 | T-02.3a | integration | store fake raises on second category | status IN_PROGRESS; first category erased and stays erased; progress shows failed + remaining; no completion outbox row |
| X-01 | T-X01a | integration | two concurrent submissions, real Postgres | exactly one request row; one 201 and one 409 |
| X-02 | T-X02a | integration | notifier fake sleeps 5s | API responds < 2s; outbox row exists |

## Fixtures to create
- `subject_with_categories(categories: dict)` — subject + personal data rows per category — T-02.1a, T-02.2a, T-02.3a
- `notifier_fake` — records calls, can be set to raise or sleep — T-01.1a, T-01.3a, T-X02a
- `run_outbox_once()` — drives the outbox worker synchronously — T-01.3a, T-02.1a

## Manual cases
- None

## Notes
- X-01 needs a real database; mark it `@pytest.mark.db` and skip on SQLite.
