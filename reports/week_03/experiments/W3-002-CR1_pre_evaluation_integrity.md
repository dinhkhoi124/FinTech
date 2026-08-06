# W3-002-CR1 — Candidate Revision 4 Pre-Evaluation Integrity

## Verdict boundary

```text
STRUCTURAL VERDICT: PASS
SEMANTIC VERDICT: AWAITING SENIOR REVIEW
EVALUATION AUTHORIZED: false
MODEL VERDICT: NOT_ESTABLISHED
```

## Exact runtime-input contract

Contract version: `critical_eval_v2_model_input_query_only_v1`.

Each Pass A row freezes `model_input_text`, its UTF-8 SHA-256, and contract
version. The single self-contained query is the sole future input to classifier,
retriever, gate, generator, verifier, ranking, overlap audit, and output
evaluation. `scenario_text` remains review metadata and does not affect Pass B
bindings or overlap evidence.

All 40 positive inputs contain the observable case facts needed for their answer
path. All 20 negatives were rewritten as revision-4 inputs. Exactly the two
registered ambiguity cases use missing context as their primary reason.

## Negative-category feasibility

The fixed distribution is structurally feasible without using ambiguity as a
surrogate reason:

| Category | Count | Primary reason |
|---|---:|---|
| Internal identifier/reference | 4 | `UNSUPPORTED_INTERNAL_REFERENCE` |
| Exact amount/approval matrix | 3 | `UNSUPPORTED_APPROVAL_MATRIX` |
| Draft-only workflow | 3 | `DRAFT_INELIGIBLE` |
| Expired-only workflow | 3 | `EXPIRED_INELIGIBLE` |
| Unresolved policy conflict | 2 | `UNRESOLVED_POLICY_CONFLICT` |
| Prompt injection | 2 | `INSTRUCTION_SOURCE_BOUNDARY` |
| Out of scope | 1 | `OUT_OF_SCOPE` |
| Ambiguous context | 2 | `AMBIGUOUS_CONTEXT` |

All 18 non-ambiguity inputs state sufficient observable context. No requested or
safe-corrective complete cover exists for the final 20 negatives. Corrective
obligations do not ask KB evidence to prove unknown customer facts.

## Semantic corrections

- `Q_V2_A_CSP03`: recognition gate supports GATE only, not REDIRECT.
- `Q_V2_A_CSD02`: escalation trigger supports THRESHOLD only, not the unstated
  immediate security action.
- `Q_V2_A_CSD04`: recognition gate is PARTIAL and cannot establish the security
  route.
- `Q_V2_A_CAR01`: escalation trigger supports BOUNDARY only, not prior
  hold/posting facts.
- Both former `Q_V2_A_TRP03` hard negatives are legitimate PARTIAL support and
  were removed from hard-negative evaluation.

Final observed Pass B counts are 97 DIRECT, 6 PARTIAL, 1,534 CONTEXTUAL, and
1,483 IRRELEVANT. Hard-negative count is zero. Exact cover-set changes are
recorded for CSP03, CSD02, and CAR01; section/document minima remain separately
derived.

## Forbidden and overlap audits

The full 60×20 forbidden matrix separates automated lexical nomination from
manual semantic judgment. Semantic attraction is true for 26/1,200 rows, down
from the invalid revision-3 value of 823. The out-of-scope cryptocurrency query
has zero banking sections that appear to answer its prediction request. Actual
draft/expired workflow attraction remains detected, and forbidden evidence never
enters obligations or covers.

Overlap is recomputed from the exact frozen `model_input_text` across all required
prior sources. Exact, normalized, high-lexical, template, and reused-ID flags are
zero. Scenario-only mutation leaves the runtime overlap audit unchanged.

## Verification

- Focused revision-4 tests: 64/64 PASS.
- Related historical W3-002 integrity tests: 68/68 PASS.
- Isolated full tracked suite: 421/421 PASS.
- Extracted standalone review bundle: 115/115 inventory files and candidate
  recomputation PASS.
- Historical W3-002 hashes: 18/18 unchanged.
- Rejected revision-3 files: 18/18 byte-preserved.
- Unauthorized execution: fails closed before inference.

Candidate revision 4 is `FROZEN_CANDIDATE /
AWAITING_SENIOR_SEMANTIC_REVIEW`. Semantic approval, evaluation authorization,
critical evaluation, and model verdict remain false/false/false/not established.
