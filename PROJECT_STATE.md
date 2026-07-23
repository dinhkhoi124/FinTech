# Project State

> This file is the concise handoff that every new Codex chat/session must read and update.

## Current status
- Project: PayResolve AI
- Current phase: Phase 1 — Banking77 benchmark
- Current week: Week 1
- P0 gate status: IN PROGRESS
- Active task: None
- Next task: `W1-002` — QUEUED / NOT STARTED; requires separate user authorization
- Last updated: 2026-07-23 by Codex

## Active objective
Complete the two controlled Week 1 baselines and final error analysis using the
verified `banking77_w1_v1` protocol without changing its locked membership.

## Current versions
- Code version: Phase 0 commit `8e321d6`; W1-001 working tree not committed
- Banking77 data version/split: `banking77_w1_v1` locked
  - upstream revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`
  - train/validation/test: 8,998 / 1,005 / 3,080
  - combined membership SHA-256: `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`
- Intent model version: none
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
- [ ] W1-002 lexical baseline
- [ ] W1-003 semantic/model-based baseline
- [ ] W1-004 evaluation/error analysis and Week 1 P0 gate

## Blockers / risks
- No W1-001 blocker. W1-002 must not start without separate user authorization.
- Seven official train/test queries overlap after case-fold + whitespace
  normalization (0 exact overlaps; all 7 label-consistent). Preserve the official
  boundary and report this evaluation limitation in W1-004.
- Week 1 remains locked to CPython 3.11.x. No ML dependency has been installed or
  selected yet; W1-002 must justify and pin only its lexical-baseline dependencies.
- Pandoc is available for DOCX; PDF export still depends on a working PDF engine
  and must be verified explicitly before claiming a PDF artifact.

## Latest verified evidence
- `py -3.11 -m unittest discover -s tests -v`: 12/12 tests passed on Python 3.11.9.
- `py -3.11 scripts/reporting/validate_project_docs.py`: required structure,
  Week 1 contracts, Python constraint, and public-safety checks passed.
- `py -3.11 scripts/data/banking77.py ... verify`: raw checksums and deterministic
  source/split/audit artifact regeneration passed.
- `reports/week_01/results/banking77_data_audit.json`: 13,083 samples, 77 intents,
  integrity counts, distributions, short-query cases, and overlap evidence.
- `data/banking77_split_manifest.json`: exact membership and per-split hashes.

## Next 3 actions
1. User reviews/commits W1-001 evidence; Codex performs no Git mutation.
2. If separately authorized, activate only W1-002 and verify `banking77_w1_v1` before use.
3. Keep W1-003/W1-004 queued; do not open a third model, P1, or Week 2.

## Handoff note
W1-001 is complete. Raw data stays ignored; provenance, checksums, audit evidence,
and locked membership are trackable. No model or benchmark metric exists. New
sessions must verify `banking77_w1_v1` and receive explicit user approval before
activating W1-002.
