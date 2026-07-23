# Project State

> This file is the concise handoff that every new Codex chat/session must read and update.

## Current status
- Project: PayResolve AI
- Current phase: Phase 1 — Banking77 benchmark
- Current week: Week 1
- P0 gate status: IN PROGRESS
- Active task: None
- Next task: `W1-003` — QUEUED / NOT STARTED; requires separate user authorization
- Last updated: 2026-07-23 by Codex

## Active objective
Complete the two controlled Week 1 baselines and final error analysis using the
verified `banking77_w1_v1` protocol without changing its locked membership.

## Current versions
- Code version: W1-001 commit `72c1c02`; W1-002 working tree not committed
- Banking77 data version/split: `banking77_w1_v1` locked
  - upstream revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`
  - train/validation/test: 8,998 / 1,005 / 3,080
  - combined membership SHA-256: `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`
- Lexical baseline version: W1-002 `word_unigram` frozen from validation
  - TF-IDF word 1-grams; LogisticRegression `C=1.0`, `lbfgs`, seed `20260723`
  - validation accuracy/macro-F1: 0.865672 / 0.862649 on 1,005 rows
  - portable local model SHA-256: `4f564e227c5f61164d51710b1a86c6e8405fa0a793cf5b71b9842f0b40d5b021`
  - official test evaluated: no; reserved for W1-004
- Semantic baseline version: none
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
- [ ] W1-003 semantic/model-based baseline
- [ ] W1-004 evaluation/error analysis and Week 1 P0 gate

## Blockers / risks
- No W1-001/W1-002 blocker. W1-003 must not start without separate user authorization.
- Seven official train/test queries overlap after case-fold + whitespace
  normalization (0 exact overlaps; all 7 label-consistent). Preserve the official
  boundary and report this evaluation limitation in W1-004.
- Week 1 remains locked to CPython 3.11.x. The W1-002 stack is pinned in
  `requirements/week1-lexical.txt`; future tasks must not silently change it.
- W1-002 validation errors cluster around neighboring rail/state intents. This is
  preliminary evidence; final taxonomy and test comparison remain W1-004 scope.
- Pandoc is available for DOCX; PDF export still depends on a working PDF engine
  and must be verified explicitly before claiming a PDF artifact.

## Latest verified evidence
- `py -3.11 -m unittest discover -s tests -v`: 15/15 tests passed on Python 3.11.9.
- `py -3.11 scripts/reporting/validate_project_docs.py`: required structure,
  Week 1 contracts, Python constraint, and public-safety checks passed.
- `py -3.11 scripts/data/banking77.py ... verify`: raw checksums and deterministic
  source/split/audit artifact regeneration passed.
- `reports/week_01/results/banking77_data_audit.json`: 13,083 samples, 77 intents,
  integrity counts, distributions, short-query cases, and overlap evidence.
- `data/banking77_split_manifest.json`: exact membership and per-split hashes.
- `reports/week_01/results/lexical_validation_metrics.json`: unigram selected over
  uni+bigrams; validation accuracy 0.865672 and macro-F1 0.862649.
- `reports/week_01/results/lexical_baseline_manifest.json`: exact runtime/config/
  data/model/evidence hashes; two consecutive runs matched all six artifacts.

## Next 3 actions
1. User reviews W1-002 implementation and validation evidence; Codex performs no Git mutation.
2. If separately authorized, activate only W1-003 and verify `banking77_w1_v1` before use.
3. Keep frozen-test W1-004 queued; do not open a third model, P1, or Week 2.

## Handoff note
W1-001 and W1-002 are complete. Raw data and the portable fitted model stay
ignored; provenance, locked membership, config, validation predictions/metrics,
confusions, and artifact hashes are trackable. The lexical numbers are validation
only, not official test claims. New sessions must verify `banking77_w1_v1` and
receive explicit user approval before activating W1-003.
