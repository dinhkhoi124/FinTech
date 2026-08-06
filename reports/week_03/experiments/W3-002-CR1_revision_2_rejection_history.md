# W3-002-CR1 — Candidate Revision 2 Rejection History

## Senior verdict

```text
FIX_REQUIRED
```

Revision 2 manifest SHA-256:
`668992392f3e0f4addeb017a0028f6bc676614910d0e1c03fb8f3e3c51a20834`.

Revision 2 external review bundle SHA-256:
`e0a447f7a71f6dc125d87dad088889d779de2c3c8892e7167d11b9a8b3b38a56`.

## Findings

1. False-abstain status was accepted from row booleans and hard-coded in derived
   audits instead of being derived from requested and safe-corrective covers.
2. At least one hard negative directly satisfied an obligation.
3. Direct-support omissions and overclaims remained in material judgments and
   minimal covers.
4. Overlap/leakage PASS was not recomputable from source rows.
5. The review ZIP could not independently execute its structural verification.

## Preservation

The revision-2 manifest and all 16 files referenced by its candidate inventory,
test output, and verification output are byte-preserved under
`reports/week_03/rejected/critical_eval_v2_revision_2/`. They are rejected
diagnostic history and are not revision-3 targets.

## Lifecycle

```text
W3-002-CR1=IN_PROGRESS / FIX_REQUIRED
candidate revision 2=REJECTED / SEMANTIC_AND_VERIFIER_CORRECTION_REQUIRED
structural_integrity_verified=false
pre_evaluation_integrity_passed=false
senior_semantic_review_approved=false
evaluation_authorized=false
critical_evaluated=false
model verdict=NOT_ESTABLISHED
Week 3 P0=BLOCKED / IN PROGRESS
Week 4=BLOCKED / NOT STARTED
```
