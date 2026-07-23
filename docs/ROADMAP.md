# Roadmap and Phase Gates

This file is a navigation summary. Detailed requirements live in `MASTER_PRD.md`.

## Phase 0 — Repository bootstrap
Reporting location: `reports/week_00/`. Week 00 is pre-execution preparation and
does not consume or start Week 1. Week 1 begins only when the user authorizes
`W1-001` after this gate.

Exit:
- agent/context/reporting structure exists
- environment and test command documented
- `PROJECT_STATE.md` and `TASKS.md` initialized
- no duplicate competing PRD

## Phase 1 / Week 1 — Banking77 benchmark
P0 gate:
- full 77 intents
- lexical baseline complete
- semantic/model baseline complete
- locked split/config reproducible
- macro-F1 + per-class + confusion/error analysis recorded
- basic preprocessing/label tests pass

Stop rule:
Exactly two main approaches are in Week 1 P0: one lexical and one semantic/model-
based baseline. Do not start a third model, model zoo, P1, or Week 2 until the two
baselines, reproducible evaluation, and error analysis pass the Week 1 gate.

## Phase 2 / Week 2 — Synthetic KB + retrieval
P0 gate:
- KB schema/guideline and versioned dataset
- valid APPROVED/DRAFT/EXPIRED metadata
- gold evidence mapping
- R0 and R1 run under controlled comparable settings
- retrieval metrics + failure analysis
- wrong-status leakage = 0 on eval

Stop rule:
If gold mapping quality is weak, stop KB expansion and improve quality.

## Phase 3 / Week 3 — Grounded RAG + safety
P0 gate:
- end-to-end pipeline works
- approved-only evidence contract enforced
- ANSWER and ABSTAIN/ESCALATE supported
- critical eval set locked
- unsupported answer, citation, abstention/safe outcome evidence
- core ablations completed
- severe failures converted to regression tests

Stop rule:
No UI or advanced judge before safety is measurable.

## Phase 4 / Week 4 — Service + incident
P0 gate:
- `/query` or equivalent end-to-end endpoint
- structured output and logs
- model/KB/index version traceability
- unit + E2E regression coverage
- one incident: reproduce → root cause → fix/rollback → rerun → regression prevention

Stop rule:
Skip Docker/advanced observability if P0 traceability/tests are incomplete.

## Phase 5 / Week 5 — Freeze + final evidence
P0 gate:
- versions frozen
- final locked evaluation run
- final evidence tables and limitations
- one deep change request
- concise report and demo ready

P1 is permitted only after the current phase P0 gate is closed.
