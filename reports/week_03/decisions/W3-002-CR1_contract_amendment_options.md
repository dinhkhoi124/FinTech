# W3-002-CR1 contract-amendment options

## Decision context

The independent 20-query feasibility audit finds 15 complete safe corrections
and five genuine abstain/escalate cases. Therefore the fixed revision-4 contract
cannot honestly produce 40 answers and 20 abstentions with the frozen KB.

Decision status: `APPROVE_CONTRACT_AMENDMENT — OPTION A`.

Senior approved Option A on 2026-08-05 using the independently reviewed
contract-feasibility bundle with SHA-256
`bc7317000005859f2e4b215cf0c4f687e5e284a4a004270d81f9f5abd0074786`.
That approval changes the task contract only. It does not approve candidate
semantics, create revision 5, or authorize evaluation.

## Option A — amend the answer subtype contract (recommended)

Keep two top-level response types and add an explicit subtype for answers:

```text
response_type:
- ANSWER
- ABSTAIN_ESCALATE

answer_subtype for ANSWER:
- STANDARD
- SAFE_CORRECTIVE
```

- `ANSWER / STANDARD`: 40 existing positive queries.
- `ANSWER / SAFE_CORRECTIVE`: 15 safety challenges where the prohibited detail
  is refused but current approved handling is complete.
- `ABSTAIN_ESCALATE`: five true no-answer safety challenges.

Recommended distribution from measured feasibility: **40 / 15 / 5**.

Trade-off: this preserves the top-level binary response contract while adding
the answer semantics needed to measure refusal of unsafe specificity without
discarding useful grounded support. It preserves all 60 current query texts for
a future separately reviewed candidate revision.

The alternative of making `SAFE_CORRECTIVE` a third top-level response type is
rejected because it needlessly changes downstream routing and obscures that the
system is still returning a grounded answer.

## Option B — amend negative categories

Keep 60 total and a Senior-approved ANSWER/ABSTAIN split, but replace infeasible
true-abstain categories with cases that genuinely lack a complete KB answer:

- external legal, regulatory, or contractual precedence;
- user-specific live account, ledger, authorization, or case-resolution facts
  unavailable to the static KB;
- out-of-scope financial, investment, or non-banking advice;
- explicitly registered ambiguity requiring rail/state clarification.

These categories are semantically feasible because the missing capability or
authority is real rather than manufactured through impossible substitute
obligations. Trade-offs: new queries require a new reviewed authoring contract,
fresh overlap review, and independent Pass B adjudication. The exact category
counts and final ANSWER/ABSTAIN split must be approved by Senior before authoring;
this package does not invent them.

## Option C — preserve the current contract

**REJECTED.** Preserving all 20 current cases as `ABSTAIN_ESCALATE` requires at
least one of:

- 15 false abstains despite complete current approved corrections;
- artificial exact-substitute/equivalent-entitlement obligations;
- ambiguity confounding in categories meant to test another safety property;
- changes to the frozen KB solely to make the evaluation contract pass.

Those conditions invalidate the intended semantic measurement. A KB change
would also be a separate scope-changing option, not a correction to this task.

## Decision

Option A is approved and formalized in
`docs/evaluation/W3-002-CR1_amended_contract.md` and
`configs/evaluation/critical_eval_v2_contract_option_a.json`. Before any future
candidate revision is authored, it must satisfy the recorded Pass B
reviewer-provenance schema, positive-support corrections, corrective-cover
wording corrections, and exact hard-negative adjudication requirements. Do not
authorize evaluation until that separately authored candidate passes independent
Senior semantic review.

Source/status boundary statements are control-plane claims established by the
exhaustive support/status audits and approved-only invariant. Factual banking
workflow claims remain evidence-cited claims and require direct eligible
APPROVED/effective support. This separation prevents a false requirement that a
KB section literally state that a private identifier or unsupported approval
matrix does not exist.
