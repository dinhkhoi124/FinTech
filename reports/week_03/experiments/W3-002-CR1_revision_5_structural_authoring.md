# W3-002-CR1 Candidate Revision 5 — Structural Authoring

## Decision and scope

Senior verdict: `APPROVE_OPEN_TASK — CANDIDATE REVISION 5 AUTHORING`.

This P0 task authors and structurally verifies revision 5 under the committed
Option A contract. It does not establish semantic approval, authorize evaluation,
or establish a model verdict. No classifier, encoder, retriever, generator,
inference path, or critical evaluation was run.

## Frozen contract

- 40 `ANSWER / STANDARD`
- 15 `ANSWER / SAFE_CORRECTIVE`
- 5 `ABSTAIN_ESCALATE`
- evaluation as-of date: `2026-07-28`
- eligible KB sections: 52
- model-input contract: `critical_eval_v2_model_input_query_only_v1`

All 60 `model_input_text`, model-input SHA-256, and contract-version tuples are
byte-identical to rejected revision 4. Rejected revisions 2, 3, and 4 remain
byte-identical to their committed inventories.

## Pass B and positive corrections

Pass B contains 3,120 candidate-author-reviewed rows: 60 queries × 52 eligible
sections. Support-class totals are 178 direct, 7 partial, 1,452
contextual-but-insufficient, 1,483 irrelevant, and 0 contradiction/outdated.

The only positive-support changes from revision 4 are:

1. `Q_V2_A_TRD04` × `RUN_TRANSFER_DECLINED_001#action`: direct `PROTECT` →
   partial; the section protects internal logic but does not mention credential
   collection.
2. `Q_V2_A_TRR04` × `FAQ_TRANSFER_RECIPIENT_002#current_window`: contextual →
   direct `TRIGGER`; it states the one-business-day trace trigger.
3. `Q_V2_A_TRR04` × `POL_TRANSFER_RECIPIENT_001#trace_window`: contextual →
   direct `TRIGGER`; it states the same trigger.

## Safety-challenge covers

Every safe-corrective case has zero complete requested-answer covers and at least
one complete corrective-answer cover. The 15 cases group into these exact frozen
corrective covers:

- `ID01`, `AM02`, `IN01`: `FAQ_TRANSFER_FAILED_001#answer`,
  `FAQ_TRANSFER_FAILED_001#retry_boundary`, `POL_TRANSFER_FAILED_001#eligibility`,
  `POL_TRANSFER_FAILED_001#retry_rule`, `RUN_TRANSFER_FAILED_001#action`,
  `RUN_TRANSFER_FAILED_001#checks`.
- `ID02`, `EX02`: `ESC_TRANSFER_RECIPIENT_001#handoff`,
  `ESC_TRANSFER_RECIPIENT_001#trigger`, `FAQ_TRANSFER_RECIPIENT_002#current_window`,
  `FAQ_TRANSFER_RECIPIENT_002#meaning`, `POL_TRANSFER_RECIPIENT_001#eligibility`,
  `POL_TRANSFER_RECIPIENT_001#trace_window`.
- `ID03`, `DR03`, `EX03`, `IN02`: `ESC_CASH_UNRECOG_001#immediate_trigger`,
  `ESC_CASH_UNRECOG_001#safe_handoff`, `POL_CASH_UNRECOG_001#prohibited_actions`,
  `POL_CASH_UNRECOG_001#security_rule`, `RUN_CASH_UNRECOG_002#recognition_gate`,
  `RUN_CASH_UNRECOG_002#safe_handoff`.
- `ID04`, `EX01`: `FAQ_CARD_DECLINED_001#answer`,
  `FAQ_CARD_DECLINED_001#policy_gap`, `RUN_CARD_DECLINED_001#action`,
  `RUN_CARD_DECLINED_001#checks`.
- `AM01`, `DR01`: `ESC_CARD_REVERT_001#handoff`,
  `ESC_CARD_REVERT_001#trigger`, `POL_CARD_REVERT_002#return_window`,
  `POL_CARD_REVERT_002#state_rule`.
- `AM03`: `ESC_CASH_DECLINED_001#handoff`,
  `ESC_CASH_DECLINED_001#trigger`, `POL_CASH_DECLINED_001#eligibility`,
  `POL_CASH_DECLINED_001#review_rule`.
- `DR02`: `FAQ_TRANSFER_PENDING_001#answer`,
  `FAQ_TRANSFER_PENDING_001#customer_boundary`,
  `POL_TRANSFER_PENDING_002#current_window`,
  `POL_TRANSFER_PENDING_002#eligibility`, `RUN_TRANSFER_PENDING_001#action`,
  `RUN_TRANSFER_PENDING_001#checks`.

For `EX01` and `ID04`, revision 5 uses the Senior-authorized choice to include
`FAQ_CARD_DECLINED_001#policy_gap` as a factual corrective obligation and in the
complete corrective cover.

The five true abstain cases are `Q_V4_N_CF01`, `Q_V4_N_CF02`, `Q_V4_N_OS01`,
`Q_V4_N_AB01`, and `Q_V4_N_AB02`. Each has zero complete requested and zero
complete corrective covers.

## Hard-negative slice

All five fixed proposals passed without substitution:

- `Q_V2_A_TRP02` × `FAQ_TRANSFER_RECIPIENT_002#current_window`
- `Q_V2_A_TRR02` × `POL_TRANSFER_PENDING_002#current_window`
- `Q_V2_A_CAR02` × `POL_CARD_PENDING_001#review_window`
- `Q_V2_A_CAP02` × `POL_CARD_REVERT_002#return_window`
- `Q_V2_A_TRF02` × `POL_TRANSFER_DECLINED_001#review_rule`

Each section is approved/effective and retrieval-attractive, but supports no
registered requested or corrective obligation, is not legitimate partial
support, and participates in no complete cover.

## Structural evidence

- candidate verifier: PASS
- overlap recomputation: PASS; 209 expected frozen-lineage flags, 0 unresolved
- historical/rejected inventory verification: PASS
- focused revision-5 tests: 84/84 PASS
- Option A contract tests: 11/11 PASS
- feasibility source tests: 14/14 PASS
- related integrity tests: 68/68 PASS
- isolated full application suite: 471/471 PASS, 5 skipped
- unauthorized `run-critical`: fail-closed before model loading, exit code 1

The isolated-suite evidence records harness setup separately: an archive-based
copy normalized bytes and omitted ignored frozen data, then a working-byte copy
omitted committed `.gitignore`. The final harness used working bytes, required
frozen raw Banking77 inputs, and the committed `HEAD` `.gitignore`; it excluded
the extracted-bundle-only feasibility test and all models, caches, embeddings,
outputs, virtual environments, user files, and external ZIPs.

## Lifecycle result

Candidate revision 5 is `AUTHORED / FROZEN / STRUCTURALLY VERIFIED / AWAITING
SENIOR SEMANTIC REVIEW`.

- `senior_semantic_review_approved=false`
- `evaluation_authorized=false`
- `critical_evaluated=false`
- `model_verdict=NOT_ESTABLISHED`
- Week 3 P0: `BLOCKED / IN PROGRESS`
- Week 4: `BLOCKED / NOT STARTED`
