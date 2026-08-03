# Week 03 Summary

## P0 objective

Grounded generation/evidence gate plus critical safety evaluation.

## Status

BLOCKED / IN PROGRESS. W3-001 implementation is DONE / REVIEWED / ACCEPTED and W3-001
overall is PARTIAL / REVIEWED / ACCEPTED. W3-001-CR1 implementation is COMPLETE.
Its original frozen-mapping result remains FAILED and is invalidated by incomplete
relevance labels; the Senior-approved post-holdout adjudication is PASS / REVIEWED
/ ACCEPTED. Senior verdict is `APPROVE_COMMIT — QUALIFIED POST-HOC PASS`. W3-002
has an internally consistent numerical run, but its critical set is INVALIDATED
and model verdict is NOT ESTABLISHED; Week 4 is BLOCKED / NOT STARTED.

## Deliverables completed

- Offline deterministic R0 pipeline with approved/effective context enforcement.
- Evidence-gated and diagnostic always-answer modes with fail-closed extraction
  and exact-quote citation verification.
- Frozen 20-case development set and preregistered 12-policy gate selection.
- Cache/network-independent tracked verifier; corrected focused/full suites pass
  69/69 and 224/224.
- Evidence Gate v2 canonical support, requested-dimension matching,
  unsupported-specificity guard, frozen 20-case holdout, and tracked verifier.
- One formal primary holdout evaluation plus one byte-identical reproduction;
  original outputs remain immutable.
- Exhaustive ten-positive mapping audit against all 52 eligible approved sections,
  three-row adjudication overlay, separate original/adjudicated artifacts, incident
  report, and fail-closed tracked verifier.
- Final no-model verification: 65/65 CR1 focused tests and 289/289 full tests PASS;
  all required tracked validators and project-doc checks PASS.

## Key evidence

| Claim | Evidence | Result | Decision |
|---|---|---:|---|
| Development isolation | gate validator | 10 positive + 10 negative; zero locked/Banking77 overlap | PASS |
| Frozen selection | 12-policy grid | selected `S0.40_C0.45` | FROZEN |
| Development safety | selected metrics | unsafe rate 0.00; negative abstention 1.00 | PASS |
| Development utility | selected metrics | positive recall 0.00; unnecessary abstention 1.00 | MATERIAL LIMITATION |
| Selected-run grounding metric | 0 answers / 0 claims | citation and unsupported-claim rates `null` | NOT APPLICABLE |
| Controlled grounding contract | mutation/regression tests | metadata, claim alignment, relevance and weight drift fail closed | PASS |
| Reproducibility | primary vs rerun | byte-identical | PASS |
| CR1 selection isolation | 9-policy design grid | `S0.40_C0.20`; zero holdout IDs used | PASS |
| CR1 holdout utility | v1 → v2 | positive recall 0.10 → 0.60; safe resolution 0.55 → 0.80 | UTILITY TARGET MET |
| CR1 family coverage | v2 positive resolutions | transfer, card_payment, cash_withdrawal | PASS |
| CR1 abstention safety | 10 negative cases | accuracy 1.00; unsafe answers 0 | PASS |
| CR1 original grounding | frozen incomplete mapping | 1 positive wrong-evidence answer | FAILED / RETAINED |
| CR1 mapping audit | 10 positives × 52 eligible sections | exactly 3 omitted direct-support sections | COMPLETE |
| CR1 adjudicated utility | frozen outputs + overlay | recall 0.70; safe resolution 0.85; 7 relevant positives | PASS |
| CR1 adjudicated safety | frozen outputs + overlay | wrong-evidence 0; unsafe answers 0 | PASS |
| CR1 citation contract | seven answered cases / 21 claims | correctness 1.00; unsupported 0; metadata failures 0 | PASS |

## P0 exit criteria

Not passed. W3-001-CR1 is accepted. W3-002 implementation and integrity incident
analysis are DONE / REVIEWED / ACCEPTED, but the critical set is invalidated and
the model verdict is not established.

## Risks / limitations

- The safety-first selected gate abstains on all development cases. This avoids
  unsafe answers but has no demonstrated development utility.
- Results are development-only and cannot be presented as final Week 3 safety.
- Classifier confidence remains diagnostic and does not alter R0 rankings.
- The original Gate-v2 evaluation failed because the frozen relevance mapping was
  incomplete. The adjudicated holdout is post-hoc, not a pristine untouched-label
  evaluation, even though corrections were exhaustive and symmetric.

## Handoff

Senior verdict is `APPROVE_COMMIT — PARTIAL BASELINE`. Review lifecycle: initial
implementation → Senior `FIX_REQUIRED` → citation metadata binding → evidence
relevance metrics → non-vacuous citation metrics → config-driven generator
weights → final approval. The implementation infrastructure is accepted, but
the selected gate is not a useful production candidate because it answered zero
of ten positive development queries. CR1 subsequently selected `S0.40_C0.20` on
design only. Preserve its original FAILED result alongside the exhaustive
three-row adjudicated PASS evidence. Senior final verdict is `APPROVE_COMMIT —
QUALIFIED POST-HOC PASS`. W3-002's original numerical run is preserved, but the
self-referential mapping audit invalidates its model verdict. Do not mark the Week
3 P0 gate passed.

## W3-002 pristine critical evaluation — 2026-08-03

The scenario-first freeze contains 60 new queries (40 ANSWER and 20
ABSTAIN_ESCALATE), four positives per intent, family counts 16/12/12, and exactly
six strict multi-document cases (two per family). All 40 positives and 20
negatives were audited against all 52 eligible approved sections before inference.
There are zero unresolved mapping omissions, false-no-answer labels, exact or
normalized overlaps, and unresolved near duplicates.

The historical evaluator reported V0 positive grounded recall 0.625, safe resolution
0.750, negative abstention 1.000, and zero unsafe negative answers, unsupported
claims, status leaks, metadata failures, or system errors. It nevertheless emitted
six positive wrong-evidence answers and completed 0/6 strict multi-document cases.
Those numbers are preserved but cannot establish a model verdict. V1 recall/safe resolution are
0.575/0.717 with the same six failures. V2 gains nine positive answers but creates
18 unsafe answers and lowers safe resolution by 0.183.

Primary and reproduction match exactly, but the pre-evaluation audit was
self-referential. Post-hoc integrity review found 20 positive mapping defects,
two hard negatives that directly support their query, six over-constrained
multi-document mappings, and eight false ABSTAIN labels. W3-002 critical-set
integrity is `INVALIDATED`, its model verdict is `NOT ESTABLISHED`, Week 3 P0 is
`BLOCKED / IN PROGRESS`, and Week 4 remains blocked. The set must not be tuned or
post-hoc adjudicated into a PASS/FAIL model verdict.

Obligation-cover recomputation splits the six exact-ID defects correctly:
`Q_CRIT_A_003`, `Q_CRIT_A_020`, and `Q_CRIT_A_040` do not semantically require
multiple sections; `Q_CRIT_A_016`, `Q_CRIT_A_028`, and `Q_CRIT_A_036` do require
two semantic sections, but same-document trigger/handoff covers exist in their
approved escalation documents. All six original multi-document labels are
over-constrained. No reviewed critical query was proven to require evidence from
two distinct documents. Integrity incident analysis is DONE / REVIEWED / ACCEPTED.

Senior final verdict is `APPROVE_COMMIT — INTEGRITY INCIDENT EVIDENCE`. The
original numerical run is DONE / PRESERVED AS HISTORICAL DIAGNOSTIC EVIDENCE;
its evaluator-reported FAILED result applies only under the invalid mapping
contract and cannot establish a model/pipeline PASS or FAIL verdict.
