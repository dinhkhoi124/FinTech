# W3-002-CR1 Revision 7 — Senior Semantic Approval

## Decision

Senior verdict: `APPROVE_SEMANTIC_INTEGRITY — CANDIDATE REVISION 7`.

Candidate `critical_eval_v2_candidate_revision_7` is approved for commit as
frozen candidate revision-7 bytes only. No candidate byte may change after this
approval.

## Approved evidence binding

- Candidate manifest SHA-256:
  `f912798ae5c02c774702ae97bee8b2b4f6c6ab12b6534e1b2a3817a969b905ef`
- Approved pre-evaluation review bundle SHA-256:
  `c91555a58f77ae845beffa1ff11734a8cc3c47e6d88f87279ba08ffb52bd5109`
- COV1 review bundle SHA-256:
  `b804fa12a4bc6f12e3852552358a29af9e071e916c92b22959fefc6ff8a629ff`
- Predecessor: candidate revision 6, manifest SHA-256
  `2f42fb4ff7159ef2735ce88418b0dbfcc414b0091476f1882a83d13e807002ad`,
  committed at `d27de987d0eb7a942c88590eec9a30bdd6ee33d8`
- Pass-B semantic delta: exactly 4 changed rows and 0 unexpected rows
- Semantic mapping changes: `Q_V2_A_TRD01`, `Q_V2_A_TRR02`, and
  `Q_V2_A_CSU03` only
- Model-input identity: 60/60 unchanged from revision 6
- Frozen distribution: 40 `ANSWER / STANDARD`, 15 `ANSWER /
  SAFE_CORRECTIVE`, 5 `ABSTAIN_ESCALATE`
- Complete covers: 92

## Approval boundary

- `senior_semantic_review_approved=true`
- `approval_scope=FROZEN_CANDIDATE_REVISION_7_BYTES_ONLY`
- `evaluation_authorized=false`
- `critical_evaluated=false`
- `model_verdict=NOT_ESTABLISHED`
- EA1: `BLOCKED_PENDING_REVISION_7_COMMIT`

This semantic approval permits the frozen candidate revision-7 bytes to proceed
to commit review. It does not authorize evaluation. Revision 6 remains a
historical semantic approval but is superseded for evaluation eligibility by
COV1 and revision 7. EA1 remains blocked until revision 7 is committed and
pushed.
