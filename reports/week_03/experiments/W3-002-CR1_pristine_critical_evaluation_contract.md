# W3-002-CR1 — Pristine Critical Evaluation Recovery

## Status and priority

- Priority: P0
- Phase: Week 3 — Grounded RAG + Safety
- Status: IN_PROGRESS / AWAITING_SENIOR_SEMANTIC_REVIEW
- Candidate revision: 4
- Evaluation version: `critical_eval_v2`
- Frozen evaluation date: `2026-07-28`
- Week 3 P0: BLOCKED / IN PROGRESS
- Week 4: BLOCKED / NOT STARTED

## Research objective

Create a pristine critical safety evaluation for the controlled future comparison
of V0 (R0 + Evidence Gate v2), V1 (R1 + Evidence Gate v2), and V2 (R0 + Always
Answer). R0 remains the selected production retriever; R1 is an ablation and
predicted intent remains diagnostic or a soft boost, never a hard filter.

This authoring task produces no model verdict. It freezes candidate evaluation
bytes before any encoder, classifier, retrieval, gate, generation, or pipeline
execution.

## Integrity objective

`critical_eval_v2` must not inherit labels, mappings, scenario/query wording,
expected outcomes, exact evidence contracts, rankings, or model outputs from the
invalidated `critical_eval_v1`. Historical incident evidence is used only as a
regression lesson: support judgments must be independently authored across the
complete 52-section approved/effective corpus, and mappings must be derived only
after those judgments are complete.

## Three-pass contract

1. Pass A freezes 60 new scenarios, queries, intents/families, requested
   dimensions, intended response types, and semantic obligations. It contains no
   mapping roles or final expected outcomes.
2. Pass B records exactly 52 independent eligible-section judgments for every
   query (3,120 rows) using DIRECT_SUPPORT, PARTIAL_SUPPORT,
   CONTEXTUAL_BUT_INSUFFICIENT, CONTRADICTION_OR_OUTDATED, or IRRELEVANT. It is
   authored without mapping fields or model artifacts.
3. Pass C derives final outcomes, acceptable evidence per obligation, canonical
   references, hard negatives, valid covers, and separate section/document cover
   minima. It cannot run until Pass B is complete.

Revision 1 violated step 2 because it generated judgments from hidden evidence
roles. Revision 2 was also rejected because its false-abstain result was
self-certified, some hard negatives were invalid, semantic support remained
overclaimed or omitted, overlap was not recomputable, and its bundle was not
standalone. Both are byte-preserved as rejected history. Revision 3 separates
requested and safe-corrective obligations, derives both covers from standalone
Pass B judgments, recomputes overlap from source corpora, and ships a standalone
verifier.

Revision 3 was rejected because exact runtime text was not frozen, replacement
negatives were confounded by missing context, lexical attraction was treated as
semantic attraction, several positive sections were over-credited, and the two
remaining hard negatives contained legitimate partial support. Revision 4 uses
`critical_eval_v2_model_input_query_only_v1`: only the frozen self-contained
`model_input_text` bytes are future classifier/retriever/gate/generator/verifier
input. `scenario_text` is authoring metadata only.

## Fixed composition

- Total: 60
- ANSWER: 40; four per each of ten focused intents
- Positive families: transfer 16, card_payment 12, cash_withdrawal 12
- ABSTAIN_ESCALATE: 20
- Negative categories: internal identifier 4; exact amount/threshold 3;
  draft-only 3; expired-only 3; superseded/current-policy conflict 2;
  override/prompt-injection 2; out-of-scope 1; ambiguous/insufficient context 2

Any intended ABSTAIN candidate with a complete safe approved answer or correction
must be rejected or replaced before freeze; target counts never override semantic
integrity.

## Authorization boundary

This Codex run may author, structurally validate, hash, report, and bundle the
candidate. Automated validation is not semantic approval. Final required state:

```text
candidate_bytes_frozen=true
structural_integrity_verified=true
pre_evaluation_integrity_passed=true
senior_semantic_review_approved=false
evaluation_authorized=false
critical_evaluated=false
package_status=FROZEN_CANDIDATE / AWAITING_SENIOR_SEMANTIC_REVIEW
```

Future execution is permitted only when all four conditions hold:

```text
pre_evaluation_integrity_passed=true
AND senior_semantic_review_approved=true
AND evaluation_authorized=true
AND critical_evaluated=false
```

## Acceptance evidence

- exact 60/40/20 and fixed family/intent/category distributions;
- exact 3,120 judgments and 52 unique eligible sections per query;
- obligation-derived outcomes with no intended/derived mismatch;
- no false abstain, invalid hard negative, forbidden-evidence use, unresolved
  leakage flag, copied material rationale, or section/document conflation;
- reproducible candidate hashes and mutation-sensitive manifest verification;
- byte-identical historical W3-002 artifacts;
- focused, related, isolated full-suite, project-doc, and Git diff checks;
- external Senior review ZIP; no stage, commit, push, or model execution.

## Controlled variables and stop boundary

The KB, frozen date, eligible-section corpus, response classes, future variants,
and safety invariants remain fixed. No new framework is introduced. Stop on any
integrity mismatch, historical drift, inference attempt, or unauthorized lifecycle
state. The candidate remains IN_PROGRESS and awaiting Senior semantic review even
after structural PASS.
