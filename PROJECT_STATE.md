# Project State

> This file is the concise handoff that every new Codex chat/session must read and update.

## Current status
- Project: PayResolve AI
- Current phase: Phase 1 — Banking77 benchmark complete
- Current week: Week 1 complete
- P0 gate status: PASSED
- Active task: none; `W1-004` complete and awaiting review/commit
- Next task: Week 2 planning or first authorized Week 2 task — QUEUED, NOT STARTED
- Last updated: 2026-07-27 by Codex

## Active objective
Preserve the frozen Week 1 benchmark and selected intent model while awaiting
review. Do not begin Week 2 without separate authorization.

## Current versions
- Code version: W1-003 commit `5f287a1`; W1-004 working tree is uncommitted
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
- KB/index/RAG eval versions: none

## Completed
- [x] Repository bootstrap and reporting workflow
- [x] W1-001 authoritative source, audit, and deterministic locked split
- [x] W1-002 frozen lexical validation baseline
- [x] W1-003 frozen semantic validation baseline
- [x] W1-004 official-test benchmark, error analysis, model selection, and gate
- [x] Week 1 P0 gate passed
- [ ] Week 2 not started

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

## Risks / limitations
- Seven normalized train/test overlaps remain in the canonical official boundary.
- Thirty reviewed errors show substantial ambiguous/underspecified label boundaries;
  five are potential annotation/taxonomy issues rather than proven mislabels.
- Classifier probabilities are uncalibrated diagnostic values; thresholding and
  OOS/OOD remain P1 and were not opened.
- Semantic is materially slower on CPU and uses an ignored ~183 MB encoder cache;
  these measurements are not production latency.

## Next 3 actions
1. User reviews and commits W1-004 evidence; Codex performs no Git mutation.
2. If separately authorized, plan or activate only the first Week 2 P0 task.
3. Keep model retuning, a third classifier, OOS/OOD, calibration, and other P1 closed.

## Handoff note
Week 1 is complete and defensible. The exact semantic model/config above is frozen
for downstream PayResolve AI, with lexical retained as fallback. Raw Banking77,
encoder weights, embeddings, caches, and fitted models remain ignored. W1-004
working-tree changes are not staged or committed, and Week 2 has not started.
