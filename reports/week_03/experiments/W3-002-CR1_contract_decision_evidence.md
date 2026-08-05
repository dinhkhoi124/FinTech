# W3-002-CR1 Option A contract-decision evidence

## Decision

Senior verdict: `APPROVE_CONTRACT_AMENDMENT — OPTION A`.

The approved feasibility bundle SHA-256 is
`bc7317000005859f2e4b215cf0c4f687e5e284a4a004270d81f9f5abd0074786`.
It contains 67 inventoried payload files, one detached self-excluding inventory,
and 68 ZIP entries. This run formalizes that decision and does not create a new
critical-evaluation candidate.

## Contract

Top-level response types remain `ANSWER` and `ABSTAIN_ESCALATE`. An answer has
subtype `STANDARD` or `SAFE_CORRECTIVE`. The future distribution is 40 standard
answers, 15 safe-corrective answers, and five true abstain/escalate cases.

A safe-corrective success refuses the prohibited/unsupported target, states the
source/status boundary, satisfies all corrective obligations, grounds every
factual banking claim in eligible APPROVED/effective evidence, uses no forbidden
evidence, invents no sensitive detail or authority, and passes claim/citation
verification. Source/status boundaries are control-plane claims established by
exhaustive support/status audits and approved-only invariants; factual banking
claims are evaluated separately against cited evidence.

The five true-abstain cases have no complete requested or corrective cover. They
cover external legal precedence, external contractual precedence, investment
prediction, and two insufficient-context cases. `ASK_CLARIFICATION` is not added
as a P0 top-level mode.

## Future revision-5 gate

The acceptance checklist requires 3,120 revision-bound Pass B rows, three exact
positive-support corrections, EX01/ID04 corrective wording resolution, separate
control-plane/factual claims, and the exact five conditional hard-negative
proposals. Failure of any proposed hard negative requires Senior review; no
substitution is allowed. These are requirements only: revision 5 was not created.

## Verification evidence

- Git preflight after workstation restart: `main`; HEAD = origin/main =
  `eb6c76d672d0800aef34f81fb134e0cf7088baab`; staged files = 0.
- Approved decision bundle: SHA-256 PASS.
- Contract schema/taxonomy/distribution/denominators/checklist: PASS.
- Rejected revision preservation: revision 2 = 17/17, revision 3 = 18/18,
  revision 4 = 19/19 files PASS.
- Historical W3-002 preservation: 18/18 PASS.
- Focused Option A contract tests: 11/11 PASS.
- Existing feasibility tests: 14/14 PASS.
- Isolated application suite: 446/446 PASS.
- Project-doc validator: PASS.
- `git diff --check`: PASS; line-ending warnings only.
- Active revision-4 candidate bytes: 19/19 PASS against rejected inventory.
- Extracted amendment bundle: 99/99 payload hashes PASS; 5/5 bundle tests and
  11/11 bundled contract tests PASS; standalone verifier PASS before and after
  tests.

Three isolation harness setup defects were retained during verification: a
shadow `tests/test_reporting/` directory, an over-broad exclusion of all
`artifacts/`, and an over-broad `models` exclusion that also removed
`configs/models`. None executed inference or changed repository files. The final
fresh-copy run excluded only the shadow directory, bundle-only tests,
`artifacts/cache`, `artifacts/models`, virtual environments, outputs, and
`docs/refactor`, while retaining tracked configuration and `artifacts/README.md`.

## Lifecycle conclusion

`senior_contract_amendment_approved=true`, but
`candidate_revision_5_created=false`, `senior_semantic_review_approved=false`,
`evaluation_authorized=false`, and `critical_evaluated=false`. Model verdict is
`NOT_ESTABLISHED`. Week 3 P0 remains `BLOCKED / IN_PROGRESS`; Week 4 remains
`BLOCKED / NOT_STARTED`.
