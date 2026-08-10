# W3-002-CR1 candidate revision 7 semantic correction

## Contract

Senior COV1 adjudication reopened revision-6 candidate semantics and authorized
exactly four Pass-B obligation removals. Revision-6 historical approval remains
immutable; evaluation was never authorized.

## Controlled semantic delta

| Query | Evidence | Revision 6 | Revision 7 |
|---|---|---|---|
| TRD01 | `POL_TRANSFER_DECLINED_001#eligibility` | STATE + BOUNDARY | STATE |
| TRD01 | `RUN_TRANSFER_DECLINED_001#checks` | STATE + BOUNDARY | STATE |
| TRR02 | `ESC_TRANSFER_RECIPIENT_001#trigger` | WINDOW + TRACE | WINDOW |
| CSU03 | `ESC_CASH_UNRECOG_001#safe_handoff` | PROHIBIT + MINIMAL | MINIMAL |

All other Pass-B semantic signatures are unchanged. Revision metadata and review
bindings were updated mechanically across the candidate package.

## Derived consequences

- Total complete covers: 94 → 92.
- TRD01 retains only the FAQ single-section complete cover.
- TRR02 retains the FAQ and policy single-section complete covers.
- CSU03 now has two two-section covers, each combining the policy prohibition
  section with either escalation or runbook minimal-reference support.
- Support-class totals remain 179/6/1,452/1,483 because all four corrected rows
  still directly support one retained obligation.

## Frozen invariants and safety boundary

- Query IDs/model-input tuples: 60/60 unchanged.
- Distribution: 40 STANDARD / 15 SAFE_CORRECTIVE / 5 ABSTAIN.
- Hard negatives: five unchanged.
- Forbidden-evidence semantics: unchanged.
- `senior_semantic_review_approved=false`.
- `evaluation_authorized=false`; `critical_evaluated=false`.
- No model, retrieval, generation, inference, or evaluation executed.

## Status

`FROZEN_CANDIDATE / AWAITING_SENIOR_SEMANTIC_REVIEW`.
