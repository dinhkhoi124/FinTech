# Prompt to give Codex — Repository Bootstrap

You are taking ownership of the PayResolve AI repository as a senior AI Engineer / Tech Lead.

Your first job is **not** to start modeling immediately. First establish a reliable repo-native project memory and reporting workflow, then execute the project phase-by-phase.

## Required behavior

1. Read the repository root `AGENTS.md` first.
2. Read:
   - `docs/PROJECT_CONTEXT.md`
   - `docs/MASTER_PRD.md`
   - `docs/ROADMAP.md`
   - `PROJECT_STATE.md`
   - `TASKS.md`
3. Audit the existing repository before creating/moving files.
4. Preserve any useful existing implementation and documents. Do not create duplicate competing sources of truth.
5. Treat `docs/MASTER_PRD.md` as authoritative scope.
6. P0 must be completed with evidence before opening P1.
7. Use Markdown as the canonical report format.
8. After every completed task, update:
   - today's `reports/week_XX/daily/YYYY-MM-DD.md`
   - `PROJECT_STATE.md`
   - `TASKS.md`
   - relevant experiment/decision/incident note
9. Do not fabricate results. Every metric in a report must trace to a real artifact/command.
10. Do not push/merge/delete major content or expose secrets without explicit instruction.

## Bootstrap tasks

### A. Inspect and reconcile
- Map the existing repo structure.
- Identify current code, datasets, configs, notebooks, experiments, tests, and reports.
- Find duplicates/stale files.
- Produce a concise reconciliation plan before destructive moves.

### B. Install the operating structure
Ensure the repo has:
- `AGENTS.md`
- `PROJECT_STATE.md`
- `TASKS.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/MASTER_PRD.md`
- `docs/ROADMAP.md`
- `docs/EXECUTION_RULES.md`
- `docs/REPORTING_POLICY.md`
- `reports/week_01 ... week_05`
- report templates
- `.agents/skills/payresolve-task-lifecycle/SKILL.md`

Adapt paths only when the existing repo has a clearly better convention.

### C. Implement lightweight report automation
After checking available dependencies, implement:
- create daily report without overwriting existing content
- validate required project/report files
- build a weekly Markdown report from canonical sources
- optionally export PDF/DOCX using a reliable available converter

Rules:
- Markdown remains source of truth.
- Generated binaries go under `reports/week_XX/exports/`.
- If PDF/DOCX conversion is unavailable, fail clearly; do not fake success.

### D. Establish reproducible developer entry points
Document exact commands for:
- environment setup
- tests
- lint/type checks if present
- training/benchmark entry points when implemented
- evaluation
- service launch later

Prefer a small number of stable commands over ad-hoc notebook-only workflows.

### E. Prepare Week 1
Break Week 1 into four executable P0 task contracts:
1. Banking77 audit + deterministic locked split
2. lexical baseline
3. semantic/model-based baseline
4. evaluation + confusion/error analysis + Week 1 gate review

For each task specify:
- task ID
- inputs
- outputs
- acceptance criteria
- test/evidence
- report update

Do not start a third model or P1 work until Week 1 P0 evidence is complete.

## Completion response
When bootstrap is complete, report:
1. repo changes
2. files created/updated
3. validation/tests run and outcomes
4. current `PROJECT_STATE`
5. Week 1 task plan
6. unresolved risks
7. suggested commit message

Then stop and wait for the next task unless explicitly asked to continue implementation.
