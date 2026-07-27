# Project State

> This file is the concise handoff that every new Codex chat/session must read and update.

## Current status
- Project: PayResolve AI
- Current phase: Phase 1 — Banking77 benchmark
- Current week: Week 1
- P0 gate status: IN PROGRESS
- Active task: none; `W1-003` complete and awaiting review
- Next task: `W1-004` queued but not started; requires separate user authorization
- Last updated: 2026-07-27 by Codex

## Active objective
Review the two frozen Week 1 validation baselines before authorizing the one-time
W1-004 evaluation and final error analysis on the untouched official test.

## Current versions
- Code version: W1-002 commit `5052afc`; documentation HEAD `9ee91c3`; W1-003
  working tree changes are not staged or committed
- Banking77 data version/split: `banking77_w1_v1` locked
  - upstream revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`
  - train/validation/test: 8,998 / 1,005 / 3,080
  - combined membership SHA-256: `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`
- Lexical baseline version: W1-002 `word_unigram` frozen from validation
  - TF-IDF word 1-grams; Logistic Regression `C=1.0`, `lbfgs`, seed `20260723`
  - validation accuracy/macro-F1: 0.865672 / 0.862649 on 1,005 rows
  - official test evaluated: no; reserved for W1-004
- Semantic baseline version: W1-003 frozen from validation
  - encoder: `sentence-transformers/all-MiniLM-L6-v2`
  - exact revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
  - normalized mean-pooled 384-dimensional embeddings; frozen encoder; CPU
  - Logistic Regression `C=1.0`, `lbfgs`, seed `20260723`, one thread
  - validation accuracy/macro-F1: 0.900498 / 0.898020 on 1,005 rows
  - official test encoded/evaluated: no/no; reserved for W1-004
- KB version: none
- Index version: none
- RAG eval set version: none

## Completed
- [x] Minimal repository structure established
- [x] Environment/setup and stable Phase 0 commands documented
- [x] Reporting workflow implemented and validated
- [x] Week 1 executable task breakdown prepared
- [x] Final source-of-truth, reduced-scope, Python strategy, and public-safety review passed
- [x] W1-001 authoritative source, audit, and deterministic locked split
- [x] W1-002 lexical validation baseline and frozen selection
- [x] W1-003 semantic validation baseline and frozen selection
- [x] DOC-001 reader-friendly MASTER_PRD split generated under `tai_lieu/`
- [ ] W1-004 evaluation/error analysis and Week 1 P0 gate

## Blockers / risks
- There is no implementation blocker. W1-004 must not begin without separate user
  authorization because it owns the first controlled frozen-test evaluation.
- Seven official train/test queries overlap after case-fold + whitespace
  normalization (0 exact overlaps; all 7 label-consistent). Preserve the official
  boundary and report this evaluation limitation in W1-004.
- Validation contains only 4–19 examples per class; W1-003 per-class comparisons
  are directional and must not be presented as official test findings.
- Cold-cache semantic reproduction requires the exact Hugging Face revision to
  remain available; the ignored local cache/model artifacts are not public Git data.
- Pandoc is available for DOCX; PDF export still depends on a verified PDF engine.

## Latest verified evidence
- Pre-commit isolated semantic module: 4/4 tests passed using `.venv-semantic`;
  direct `payresolve_ai` import resolved from `src/payresolve_ai`. The same
  interpreter passed the full suite, 20/20 tests.
- W1-003 validation: accuracy 0.900498 and macro-F1 0.898020; deltas versus frozen
  lexical validation are +0.034826 and +0.035371.
- W1-003 primary/repro total runtimes: 79.315 s / 70.651 s on CPU; both were fresh
  embedding-cache runs.
- Stable classifier, metrics, predictions, per-class, confusion, embedding-manifest,
  model-provenance, and comparison hashes matched across independent refresh runs.
- Encoder snapshot is pinned to revision `1110a243...b4d41`; model dimension,
  pooling, normalization, frozen state, and snapshot file hashes are recorded.
- `test_evaluated=false` and `test_encoded=false` in W1-003 manifests.
- Final repository tests and validators are recorded in the 2026-07-27 daily report.

## Next 3 actions
1. User reviews W1-003 implementation, evidence, and working-tree changes.
2. If separately authorized, activate only W1-004 and verify both frozen configs
   and `banking77_w1_v1` before the single official-test evaluation.
3. Keep every third model, P1, and Week 2 task closed.

## Handoff note
W1-001, W1-002, and W1-003 are complete. Both baseline metrics currently reported
are validation-only. Raw data, downloaded encoder files, embeddings, and fitted
classifier parameters remain ignored; provenance, configs, aligned predictions,
metrics, comparisons, and hashes are trackable. No Git mutation beyond working-tree
file edits was performed, and W1-004 has not started.
