# Project State

> This file is the concise handoff that every new Codex chat/session must read and update.

## Current status
- Project: PayResolve AI
- Current phase: Phase 2 — Controlled Synthetic KB + retrieval
- Current week: Week 2
- P0 gate status: IN PROGRESS; W2-001 DONE / REVIEWED / ACCEPTED
- Active task: none
- Next task: `W2-002` gold evidence mapping — QUEUED, NOT STARTED
- Last updated: 2026-07-28 by Codex

## Active objective
W2-001 received Senior verdict `APPROVE_COMMIT` and is accepted in the current
repository history. Do not begin gold evidence mapping, retrieval, indexing,
generation, or any P1 work.

## Current versions
- Code version at W2-001 start: W1-004 commit
  `7c60110eab7cd18e538b274803f31879179d9e46`
- Banking77 protocol: `banking77_w1_v1`
  - upstream revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`
  - train/validation/test: 8,998 / 1,005 / 3,080
  - membership SHA-256: `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`
- W1-004 evaluation config SHA-256:
  `a6ac09654884528aa6ccabf784a349304eddecb3ccb0add680000ad4f6272a40`
- Frozen lexical candidate: `lexical_word_unigram`
  - validation accuracy/macro-F1: 0.865672 / 0.862649
  - official-test accuracy/macro-F1: 0.878247 / 0.878362
- Frozen semantic candidate: `semantic_all_minilm_l6_v2`
  - encoder revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
  - validation accuracy/macro-F1: 0.900498 / 0.898020
  - official-test accuracy/macro-F1: 0.908117 / 0.908075
- Selected downstream intent model: `semantic_all_minilm_l6_v2`
  - config: `configs/models/banking77_semantic_w1.json`
  - config SHA-256: `de4ebff80c7e758339def8b35a31e4c3e5b7723b2e2eec8493e818ae8887b50b`
  - fallback: `lexical_word_unigram`
- Official frozen test: EVALUATED under W1-004; no post-test tuning
- KB version: `payresolve_synthetic_kb/kb_v1` — CONTENT FROZEN; VALIDATOR FIX VERIFIED
  - evaluation as-of date: `2026-07-28`
  - documents/eligible: 36 / 26
  - canonical dataset SHA-256:
    `e54a21529c516659265f82ca4818e1c844c05e8e7d7a692b02154115869d4c88`
  - config SHA-256:
    `d6ff1adc158c41cd6e9c9a418aa22bd2696cd0be80343a174b3f74146f74a909`
  - schema SHA-256:
    `ee9f959cef795b35482db4f0a9868f5981ec8291e3f228d63a289fddeae3dc29`
- Index/RAG eval versions: none

## Completed
- [x] Repository bootstrap and reporting workflow
- [x] W1-001 authoritative source, audit, and deterministic locked split
- [x] W1-002 frozen lexical validation baseline
- [x] W1-003 frozen semantic validation baseline
- [x] W1-004 official-test benchmark, error analysis, model selection, and gate
- [x] Week 1 P0 gate passed
- [x] W2-001 controlled synthetic KB — DONE / REVIEWED / ACCEPTED
- [ ] W2-002 gold evidence mapping — NOT STARTED
- [ ] W2-003 retrieval R0/R1 — NOT STARTED

## Latest verified evidence
- Official test contains 3,080 rows, all 77 intents, exactly 40 rows per intent.
- Lexical: accuracy 0.878247, macro-F1 0.878362, 2,705 correct, 375 errors.
- Semantic: accuracy 0.908117, macro-F1 0.908075, 2,797 correct, 283 errors.
- Semantic deltas: accuracy +0.029870 and macro-F1 +0.029713.
- Paired outcomes: 2,611 both correct, 94 lexical-only, 186 semantic-only,
  and 189 both wrong.
- Per-class F1: semantic improved 49, regressed 21, unchanged 7; no regression
  reached absolute 0.20.
- Both models correctly classified all seven normalized-overlap rows; excluding
  them changes either aggregate metric by less than 0.0003.
- Primary/repro stable outputs were byte-identical; CPU runtimes varied as expected.
- W1-004 artifact validator passed with test encoded/evaluated recorded true.
- W2-001 validator passed: 36 schema-valid English synthetic documents, with
  APPROVED/DRAFT/EXPIRED counts 26/5/5 and eligible count 26.
- All 10 locked intents have at least two eligible documents and two document
  types; exact `reverted_card_payment?` maps to safe slug
  `reverted_card_payment`.
- Four complete version families and 12 explicit hard-negative relationships
  passed reference and lifecycle validation.
- First-28 quality gate passed with 20 eligible documents, complete coverage,
  four version families, and nine fully resolved hard-negative relationships.
- Exact/normalized duplicate groups and token-Jaccard candidates at threshold
  0.72 were both zero; manual review completed.
- Senior-review hardening closed the schema/lifecycle/hard-negative false-pass
  defect without changing canonical KB bytes. All nine direct mutations fail
  with explicit error codes; the first-28 gate counts only valid structures.
- W2-001 focused tests passed 29/29; full repository suite passed 56/56; project
  reporting validator passed.

## Risks / limitations
- Seven normalized train/test overlaps remain in the canonical official boundary.
- Thirty reviewed errors show substantial ambiguous/underspecified label boundaries;
  five are potential annotation/taxonomy issues rather than proven mislabels.
- Classifier probabilities are uncalibrated diagnostic values; thresholding and
  OOS/OOD remain P1 and were not opened.
- Semantic is materially slower on CPU and uses an ignored ~183 MB encoder cache;
  these measurements are not production latency.
- KB timelines and workflows are fictional research controls, not real policy.
- Lightweight lexical near-duplicate screening does not prove absence of semantic
  overlap.
- Gold evidence quality and retrieval performance remain unmeasured until
  separately authorized W2-002/W2-003.

## Next 3 actions
1. Commit and push only the accepted W2-001 scope.
2. Activate W2-002 only under a separate authorization.
3. Keep retrieval, generation, model retuning, and all P1 work closed.

## Handoff note
Week 1 is complete and defensible. The exact semantic model/config above is frozen
for downstream PayResolve AI, with lexical retained as fallback. Git preflight on
2026-07-28 confirmed clean synchronized `main` at W1-004 commit `7c60110`.
W2-001 received Senior verdict `APPROVE_COMMIT` after validator hardening,
14 regression tests, and nine direct mutation failures. W2-001 is accepted in
the current repository history. W2-002 and W2-003 have not started.
