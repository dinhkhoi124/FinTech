# W3-002-CR1-EA1 Execution Readiness

Active readiness revision: **9**. Candidate revision: **7**.

## Purpose

This contract prepares deterministic, fail-closed execution infrastructure for
the frozen W3-002-CR1 candidate revision 7. It does not authorize model loading,
retrieval, generation, inference, gold loading before raw freeze, or critical
evaluation.

## Frozen candidate binding

- Candidate revision: 7
- Candidate commit: `18a1840f39fef8f07337ff357f7991292389bae9`
- Candidate manifest SHA-256:
  `f912798ae5c02c774702ae97bee8b2b4f6c6ab12b6534e1b2a3817a969b905ef`
- Mapping SHA-256:
  `cc9e82adbb97fd8054e58d3d6548ca03b15046bb37eca53ef9aa529dc4ec12f1`
- Distribution: 40 STANDARD / 15 SAFE_CORRECTIVE / 5 ABSTAIN_ESCALATE

## Readiness gates

- Candidate bytes and 23 manifest artifacts must verify exactly.
- Runtime payloads contain only query ID, model-input text, and its SHA-256.
- Runtime assets and encoder snapshot are content-hash bound before model load.
- Execution requires a separate committed Senior authorization record with
  topology `parent(A)=R`.
- Raw outputs are write-once and must freeze before any gold/evaluator load.
- State transitions and their direct input/output hashes are validated exactly.
- Canonical evaluator covers are minimum-cardinality complete covers. They must
  equal the frozen candidate set across all 55 answerable queries (92 covers).
- Larger inclusion-minimal covers remain noncanonical diagnostic evidence.
- Safety rules must pass all six COV1 regressions and the target-specific
  adversarial matrix with zero false positives and zero false negatives.
- Readiness revision 9 requires explicit target classification for all 15
  SAFE_CORRECTIVE queries, 11 canonical disclosure targets across eight
  disclosure-capable queries, 38 exact Senior safety rows, a pre-evaluator
  fixture-quality gate, complete per-target grammar coverage, a full
  per-mutation campaign, and eight concrete self-adversarial categories.
- Authorization commit A may update only the authorization record, canonical
  lifecycle files, week summary, and `daily/2026-08-11.md`; the stale
  `daily/2026-08-10.md` path is forbidden.
- Active generated readiness/runtime provenance must bind revision 7; historical
  revision-6 references and detector fixtures are classified separately.

## Current state

`FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_AUTHORIZATION_REVIEW`.
`evaluation_authorized=false`, `critical_evaluated=false`, and
`model_verdict=NOT_ESTABLISHED`. Candidate revisions 8 and 9 do not exist.

Readiness revision 7 is rejected review history, bound to external ZIP SHA-256
`dc72ab6d074c3dd3eb3391586ec783c8b287abbb44114e872e048c4cf5c9757c`.
This does not reject or modify Candidate Revision 7.

Readiness revision 8 is also rejected review history:
`REJECTED_BY_SENIOR / DISCLOSURE_TARGET_COVERAGE_INCOMPLETE /
ADVERSARIAL_FIXTURE_TARGET_CONSTRUCTION_INVALID`. Its external review ZIP is
bound at SHA-256
`3291975173dff7e8afb0da4ab368d32e8f1913020bc9951f5e56b3b8686fe218`.
Revision 9 corrects ID02/ID03/ID04 disclosure ordering and constructs every
adversarial disclosure fixture from its canonical bare target phrase.

## Senior-reviewed predecessor: readiness revision 10

Revision 10 closes only F1 post-freeze subtype separation, F2 narrow registered
disclosure guard, and F3 strict raw provenance. Raw subtype is null-only;
STANDARD/SAFE_CORRECTIVE is derived only after freeze. The literal registry is
limited to the current eight disclosure-capable queries and 11 canonical targets
and contains zero invented literals. One provenance validator is enforced before
persistence, freeze, and evaluator/gold load.

Senior review changed its status to `SENIOR_REVIEWED /
F3_BATCH_MEMBERSHIP_DEFECT_FOUND` because exact run-level membership was not
enforced before persistence.

## Active closure: readiness revision 11

Revision 11 closes only that F3 defect. `validate_raw_run_binding` requires 60
rows, 60 unique query IDs, and exact equality with the frozen runtime-payload
query set before delegating to the settled per-row validator. The same batch
guard is used before persistence, before freeze, and before evaluator/gold load.
F1 and F2 remain closed and regression-only.

Status is `FROZEN_READINESS_PACKAGE /
AWAITING_SENIOR_AUTHORIZATION_REVIEW`. `evaluation_authorized=false`,
`critical_evaluated=false`, and `model_verdict=NOT_ESTABLISHED`.

## Readiness Revision 12 — authorization date topology only

Revision 11 was Senior-approved, committed, and pushed at
`c7bc68bbef51684f6ff4ab7a672ca78af4cbbadd`. It remains accepted for F1, F2,
F3 row provenance, and F3 batch membership provenance. Revision 12 supersedes
it only because authorization commit A is now planned for 2026-08-12 while the
committed topology allowed only the prior daily report.

The authoritative allowlist now contains exactly the authorization record,
`PROJECT_STATE.md`, `TASKS.md`, the Week-3 summary, and
`reports/week_03/daily/2026-08-12.md`. The 2026-08-11, 2026-08-10,
2026-08-13, arbitrary daily, Candidate, and execution/source paths are rejected.
The amendment is explicit and contains no wall-clock routing.

Revision 12 is `FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_REVIEW` with reason
`AUTHORIZATION_DAILY_REPORT_DATE_ROLLOVER`. `evaluation_authorized=false`,
`critical_evaluated=false`, and `model_verdict=NOT_ESTABLISHED`; no
authorization record A or evaluation output exists.
