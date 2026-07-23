---
name: payresolve-task-lifecycle
description: Mandatory lifecycle for implementing, experimenting, debugging, evaluating, or documenting PayResolve AI tasks.
---

# PayResolve Task Lifecycle

Use this workflow for every material task.

## 1. Orient
Read:
- root `AGENTS.md`
- `PROJECT_STATE.md`
- `TASKS.md`
- current phase in `docs/ROADMAP.md`
- relevant section of `docs/MASTER_PRD.md`
- today's/this week's existing report notes

Determine:
- task ID
- P0/P1/P2
- current phase gate
- acceptance criteria
- files/results likely affected

## 2. Inspect before changing
Search the repository first.
Never create a second implementation, config, dataset, or report that duplicates an existing source without a clear migration reason.

## 3. Plan
For non-trivial work, write a short execution plan:
- goal
- steps
- verification
- report/state updates

For experiments, state the hypothesis and controlled variables before running.

## 4. Execute
Implement the smallest coherent change that satisfies the task.
Preserve reproducibility and safety invariants.
Do not widen scope opportunistically.

## 5. Verify
Run the most relevant available:
- unit tests
- integration/E2E tests
- validation scripts
- benchmark/eval scripts
- lint/type checks if configured

Record exact commands and actual outcomes.
If something cannot run, state why and do not pretend it passed.

## 6. Convert failure to evidence
For important failures:
- reproduce
- isolate root cause
- fix
- add regression protection where appropriate
- record lesson

## 7. Update project memory
Before finishing:
- update `PROJECT_STATE.md`
- update `TASKS.md`
- update today's daily report
- update experiment/decision/incident notes when relevant
- update weekly summary if a milestone/gate changed

## 8. Completion response
Report:
- what changed
- verification/results
- unresolved risks
- docs/report files updated
- next recommended task
- suggested commit message

Do not push or merge unless explicitly asked.
