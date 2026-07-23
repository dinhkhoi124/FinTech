# Reporting Policy

## Objective
Mentor-facing repository must contain source code plus a large `reports/` folder organized by week/sprint, with work noted by day.

## Week numbering

- `reports/week_00/` is repository bootstrap/pre-execution evidence only.
- `reports/week_01/` begins when the user authorizes `W1-001`; bootstrap activity
  on 2026-07-23 is not duplicated into Week 1.
- `reports/week_01/` through `reports/week_05/` correspond to the five PRD weeks.

## Canonical format
Markdown is the source of truth.

Why:
- diffable in Git
- easy for Codex to update safely
- supports code/metric links
- avoids binary merge drift

PDF/DOCX are generated deliverables, not independently edited sources.

## Required updates after each completed task
Codex must:
1. Append/update today's `reports/week_XX/daily/YYYY-MM-DD.md`.
2. Update `PROJECT_STATE.md`.
3. Update `TASKS.md`.
4. Create/update experiment, decision, or incident note if relevant.
5. Link evidence paths rather than copying unverifiable numbers.

## Daily report minimum content
- Goal
- Task IDs
- Work completed
- Files changed
- Commands/tests/evaluations run
- Actual results/metrics
- Problems and root cause/fix
- Decisions/trade-offs
- Evidence/artifact paths
- Next step
- Suggested commit message

## Weekly summary
Update progressively, but finalize only at week close:
- P0 objective and status
- completed deliverables
- key metrics/results
- important error analysis
- decisions
- unresolved risks
- P0 exit criteria checklist
- P1 items opened/deferred
- next-week handoff

## Export policy
At mentor-review or week-close:
- build week report from canonical Markdown
- export to PDF and/or DOCX only if the environment supports a reliable converter
- generated artifacts go under `reports/week_XX/exports/`
- generated files must include source commit hash/date when possible

Never manually edit generated PDF/DOCX as a competing source of truth.
