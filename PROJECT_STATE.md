# Project State

> This file is the concise handoff that every new Codex chat/session must read and update.

## Current status
- Project: PayResolve AI
- Current phase: Phase 0 — Repository bootstrap
- Current week: Week 0 / Bootstrap
- P0 gate status: PASSED — ready for user commit/review
- Active task: None
- Next authorized task: `W1-001` — NOT STARTED; requires explicit user approval
- Last updated: 2026-07-23 by Codex

## Active objective
Establish the repository operating system, context, reporting workflow, and reproducible development entry points before Week 1 implementation.

## Current versions
- Code version: not frozen
- Banking77 data version/split: not created
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
- [ ] Week 1 task breakdown reviewed/approved by user

## Blockers / risks
- No remaining Phase 0 blocker. Week 1 must not start before user commit/review
  and explicit approval of `W1-001`.
- Week 1 is locked to CPython 3.11.x. The installed Python 3.11.9 passed the
  Phase 0 suite, but the existing `.venv` is Python 3.14.3 with only pip and must
  be recreated after review before Week 1 ML/data execution.
- Week 1 ML/data dependencies remain intentionally unselected; `W1-001` must pin
  and verify only the dependencies needed for its P0 data contract.
- Pandoc is available for DOCX; PDF export still depends on a working PDF engine
  and must be verified explicitly before claiming a PDF artifact.

## Latest verified evidence
- `py -3.11 -m unittest discover -s tests -v`: 6/6 tests passed on Python 3.11.9.
- `py -3.11 scripts/reporting/validate_project_docs.py`: required structure,
  Week 1 contracts, Python constraint, and public-safety checks passed.
- The same 6/6 bootstrap tests passed on the retained Python 3.14.3 `.venv`; this
  does not establish ML dependency support on Python 3.14.
- `reports/week_00/daily/2026-07-23.md`: exact bootstrap work and commands.
- `reports/week_00/exports/week_00_report.md`: generated weekly Markdown aggregate.
- Final Git audit: 1 tracked modified file (`README.md`), 73 untracked bootstrap
  files, no staged files, no protected tracked paths, and one authoritative PRD.

## Next 3 actions
1. User reviews/commits the Phase 0 checkpoint; no Git mutation is performed by Codex.
2. After explicit approval, recreate `.venv` with Python 3.11 and activate only `W1-001`.
3. Keep `W1-002` through `W1-004` queued; do not open P1, a third model, or Week 2.

## Handoff note
Phase 0 final review passed but Week 1 has not started. No Banking77 data, split,
model, benchmark metric, or RAG artifact exists. New sessions must inspect the
repository and receive explicit user approval before activating `W1-001`.
