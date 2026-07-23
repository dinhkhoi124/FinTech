# Execution Rules

## Definition of Ready
A task is ready when:
- phase/week is known
- task ID exists
- P0/P1/P2 is known
- expected artifact/result is known
- acceptance criteria are testable
- relevant input data/dependencies are available

## Definition of Done
A task is done only when applicable evidence exists:

`Implementation → Test/Evaluation → Result → Analysis/Decision → Report → State update`

Code running without verification is not done.

## Experiment contract
Every material experiment should record:
- hypothesis
- controlled setup
- changed variable(s)
- fixed variables
- dataset/split/version
- model/config/seed
- metrics
- raw result artifact path
- result interpretation
- error analysis
- decision / next step

## Engineering decision contract
For non-trivial choices:
- context/problem
- considered options
- chosen decision
- trade-offs
- consequences
- rollback/change condition

## Bug contract
For important bugs:
`Reproduce → Root cause → Fix → Regression test → Lesson`

## Change control
When the user asks for a new feature:
1. Map it to P0/P1/P2 and current phase.
2. Check whether it risks the current P0 gate.
3. If it expands scope, record the decision before implementing.
4. Do not silently replace the PRD.

## Evidence policy
Claims in README/reports must be backed by:
- test output
- metric file
- config
- figure/table
- trace/log
- code path
- or explicitly labeled qualitative/manual review

Never fabricate missing evidence.
