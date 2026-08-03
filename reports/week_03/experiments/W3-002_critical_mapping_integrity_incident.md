# W3-002 Critical Mapping Integrity Incident

Senior final verdict: `APPROVE_COMMIT — INTEGRITY INCIDENT EVIDENCE`.

W3-002 implementation and this integrity incident analysis are DONE / REVIEWED /
ACCEPTED. The original numerical run is DONE / PRESERVED AS HISTORICAL DIAGNOSTIC
EVIDENCE. Its evaluator-reported FAILED result was produced under the invalid
mapping contract and does not establish a model/pipeline verdict.

## Reproduce

Senior review traced `audit_mappings()` and reproduced that
`directly_supporting_evidence_ids` was assigned from the mapping's own gold and
acceptable IDs. The function then emitted all 52 eligible IDs as reviewed, an
empty omission set, and `PASS_NO_OMISSION`. Negative rows trusted the dataset's
integer `approved_sections_reviewed == 52` and self-certified no complete answer.

## Root cause

The audit artifact copied the mapping's own gold/acceptable IDs into the
"directly supporting" field and hard-coded that 52 sections were reviewed. It
therefore could not detect missing direct evidence, over-constrained
multi-document labels, incorrectly assigned hard negatives, or false ABSTAIN
labels. The mapping and its purported audit were not independent sources.

## Concrete examples

- `Q_CRIT_A_004`: `POL_TRANSFER_FAILED_001#retry_rule` was a hard negative even
  though it directly establishes that retry is allowed only after terminal
  failure, answering why retry is unsafe while pending.
- `Q_CRIT_A_020`: `POL_CARD_PENDING_001#review_window` alone supplies the review
  action and duplicate-dispute prohibition; exact two-document gold was
  over-constrained.
- `Q_CRIT_A_040`: both `ESC_CASH_UNRECOG_001#safe_handoff` and
  `RUN_CASH_UNRECOG_002#safe_handoff` cover safe routing and no credentials, but
  exact-all-gold rejected equivalent support.
- `Q_CRIT_N_014` and `Q_CRIT_N_015`: active approved policy gives complete safe
  corrections to superseded timing instructions, so ABSTAIN labels were false.

## Impact

The pre-evaluation claims `mapping_audit_passed=true`, zero omissions, and zero
false no-answer labels are unsupported. Although primary/reproduction outputs
remain byte-identical and their historical metrics recompute, neither the
reported PASS nor FAILED interpretation can establish model performance. W3-002
critical-set integrity is INVALIDATED and its model verdict is NOT ESTABLISHED.

Independent post-hoc review found 20 positive mapping defects, two hard negatives
that directly support their queries, six exact-ID multi-document mappings
over-constrained, and eight false ABSTAIN labels (`Q_CRIT_N_008` through
`Q_CRIT_N_015`). Obligation-cover recomputation separates the six into:

- single section sufficient: `Q_CRIT_A_003`, `Q_CRIT_A_020`, `Q_CRIT_A_040`;
- multiple semantic sections required but one document sufficient:
  `Q_CRIT_A_016`, `Q_CRIT_A_028`, `Q_CRIT_A_036`.

The second group needs a trigger plus safe handoff: overdue trace for `A_016`,
overdue reversal for `A_028`, and repeated ATM decline for `A_036`. In each case,
both sections can come from one approved escalation document. All six original
multi-document labels are therefore over-constrained, and no reviewed query was
proven to require two distinct documents.

## Containment

- Preserve original scenarios, data, manifest, rankings, outputs, reproduction,
  metrics, claims, and outcome artifacts byte-for-byte.
- Do not rerun encoder, retrieval, generator, primary, or reproduction.
- Reject the original `audit_mappings()` path and distinguish internally
  consistent runtime artifacts from invalid mapping integrity.
- Keep Week 3 P0 and Week 4 blocked; do not create `critical_eval_v2` here.

## Regression requirements

The focused suite now proves that support cannot be derived from mapping roles,
each audit row carries 52 unique valid section judgments and a unique rationale,
direct-support hard negatives fail integrity, exact-ID over-constraint is flagged,
equivalent evidence can satisfy an obligation, current-policy corrective answers
invalidate false abstentions, self-certified manifests are rejected, and invalid
mapping integrity prevents a final model verdict.

The corrected verifier enumerates all section-level evidence subsets that cover
every reviewed obligation. It computes minimum section count and minimum distinct
document count separately from parsed `DOCUMENT#SECTION` identities. Two sections
in one document imply multi-section need, not multi-document need. It also fails
closed on invalid evidence identities, metadata disagreement, stale section or
document minima, same-document covers ignored by a multi-document claim, malformed
obligations, hard-negative drift, stale reason codes, and stale summary subgroups.

## Derived artifact hash transition — obligation coverage v3

- Positive integrity audit:
  `6f90e14140d9298660c69f2449de44d29dbaa7542d2fde5d232b701c04b6a1c0`
  -> `3eb87d6b84eed1af20cdecb8d58128357da2174aebb97efddba26bd7fcb7533e`
- Negative integrity audit remains
  `93acffe5a4e933b8287cb2adf0dc60b0fa5fc740009c456a58a05d4333923959`.
- Independent support judgments remain
  `667a0aa6e776232ad93018bd19494422df2454a1ff2eb6b8c6a3299fe2a8cfdf`.
- Incident summary:
  `e990c130511b6459890cef571f6f66887314f9e480742cd9a081ac6cef50bd79`
  -> `7a65d6aadf76007cec4b70934de864e78b2113b19420b8b630fe5dca41466eb2`.
- Integrity config:
  `02d6d5b7b2c143a4b161e690f9f84192b73dcba008ae11982902c99025bbe15e`
  -> `15ae4d09e257ee7aa381760be3c1e37a702bfc1683d24c0bbcf03b8de9c543ca`.
- Integrity verification output:
  `8b1af206db01dae96b3ef22c265a607cb3f7bca8a8c18bd82f1c64251ad048e0`
  -> `a480cf3627c8e07af81dae026cf87535a2920b3214bf2442c5d1778df698e190`.

Only derived classification columns, subgroup summaries, and their frozen hashes
changed. Original W3-002 mappings and runtime artifacts remain byte-identical.

## Derived artifact hash transition — section/document correction v4

- Positive integrity audit:
  `3eb87d6b84eed1af20cdecb8d58128357da2174aebb97efddba26bd7fcb7533e`
  -> `89b2f7454e28f6b33db15b24843b4d1e9c55d4777e7e821772f98b0e9a1ea4fc`.
- Negative integrity audit remains
  `93acffe5a4e933b8287cb2adf0dc60b0fa5fc740009c456a58a05d4333923959`.
- Independent support judgments:
  `667a0aa6e776232ad93018bd19494422df2454a1ff2eb6b8c6a3299fe2a8cfdf`
  -> `861d19e2cdb5ff937d3f4e2c9eb69f94efbd3b3599531adcb143bb91aa443f81`.
- Incident summary:
  `7a65d6aadf76007cec4b70934de864e78b2113b19420b8b630fe5dca41466eb2`
  -> `8684d91a948d2763efea0b59ec7e2add97434d26e55738e55069a4f34dafec54`.
- Integrity config:
  `15ae4d09e257ee7aa381760be3c1e37a702bfc1683d24c0bbcf03b8de9c543ca`
  -> `6bd25570bd233bfa72203b354ae1164f43d3f8bbaa0d9e246727c6e5550dc753`.
- Integrity verification output:
  `a480cf3627c8e07af81dae026cf87535a2920b3214bf2442c5d1778df698e190`
  -> `3bc3c9bc4c719a02b72aa47e0a8e398fb7c7820d62f7b0e3f08885eef0cea905`.

The support-judgment hash changed only because `A_016`, `A_028`, and `A_036`
were corrected from multi-document necessary to multi-section/single-document.
Original critical data, mapping, rankings, outputs, reproduction, metrics, claim
audit, and outcome classes remain byte-identical.

## Next decision

Use a separate Senior-reviewed contract to decide whether to author a fresh
critical set or close Week 3 with the limitation. A future evaluator should define
semantic obligations, each with independently reviewed alternative evidence IDs:

```json
{
  "required_obligations": [
    {"obligation_id": "WAIT_WINDOW", "acceptable_evidence_ids": ["POL_X#window", "FAQ_X#window"]},
    {"obligation_id": "SAFE_HANDOFF", "acceptable_evidence_ids": ["RUN_X#handoff", "ESC_X#handoff"]}
  ]
}
```

A response succeeds only when every obligation is supported; it must not require
one exact preselected document ID when reviewed equivalent evidence exists.
