# W2-001 Manual Quality Review

## Review scope

Manual review covered all 36 titles and section bodies, the four complete version
families, the 12 hard-negative relationships, intent/type coverage, the
intentional policy gap, and the high-risk multi-document case.

## Findings

- All content identifies fictional PayResolve Demo Bank and carries the common
  synthetic disclaimer.
- No real customer data, phone number, institution policy, proprietary document,
  credential request, or account-specific advice was found.
- All version histories differ in handling windows, eligibility, escalation, or
  workflow—not metadata alone.
- Four attractive drafts are explicit but ineligible.
- Three reviewed expired/current pairs contain deliberate, resolvable conflicts.
- All 12 hard negatives share meaningful vocabulary while retaining a decisive
  transaction-state or payment-rail distinction.
- `cash_withdrawal_not_recognised` cannot resolve through ordinary troubleshooting:
  policy, runbook, and escalation guide consistently require security handling.
- `declined_card_payment` intentionally lacks approved policy evidence; its FAQ
  explicitly warns that FAQ/runbook content is not policy authority.
- The multi-document unrecognized-cash case has non-duplicative roles: policy
  establishes priority, runbook controls checks, and escalation guide controls
  handoff.

## Duplicate review

- Exact/normalized duplicate groups: zero.
- Deterministic normalized token-set Jaccard threshold: `0.72`.
- Candidates at or above threshold: zero.
- The four version families were still manually compared because versioned
  documents are expected to share vocabulary below the threshold.
- Conclusion: no unresolved duplicate was found. This lightweight lexical method
  does not claim perfect semantic duplicate detection.

## Review decision

`PASS`. Senior AI Engineer verdict: `APPROVE_COMMIT`. The content review and
subsequent validator-hardening evidence are accepted in the current repository
history. Revisit content only if a separately authorized W2-002 gold-mapping task
exposes an evidence ambiguity; do not change it in response to locked retrieval
metrics.

## Senior-review correction

The initial manual content decision remains valid, but it did not compensate for
a machine-validator false-pass defect. After reproducing that defect, the
standard-library validator was hardened to enforce the required schema mirror,
exact lifecycle chains, and complete hard-negative relationship contract.
Fourteen new negative tests and nine direct mutations now fail explicitly, while
the unmodified 36-document KB passes. This review therefore supports content
quality and manual meaningful-change judgments; structural validity is supported
separately by the regenerated validator evidence and regression suite.
