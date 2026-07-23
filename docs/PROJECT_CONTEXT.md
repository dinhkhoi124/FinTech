# Project Context — PayResolve AI

## Project
**PayResolve AI — Banking Intent Classification & Grounded RAG for Payment Support**

Research Question:

> Làm thế nào phân loại fine-grained banking intent và sinh câu trả lời chỉ dựa trên FAQ, Policy và Runbook đã được phê duyệt?

## Internship objective
The repository must demonstrate that a new-graduate AI Engineer can:

`Problem definition → Data understanding → Baseline → Evaluation → Error analysis → Synthetic data engineering → Retrieval → Grounded generation → Safety → API/tests/logging/versioning → Incident debugging → System design`

The success signal for mentors is ownership and evidence, not the number of tools used.

## System target
`User Query → Intent Classification → Retrieval → Approved/Effective Filter → Evidence Validation → Grounded Generation → Citation Check → Answer | Abstain | Escalate`

## P0 outcome by phase
### Week 1
Full Banking77 benchmark:
- 1 lexical baseline
- 1 semantic/model-based approach
- accuracy, macro-F1, per-class metrics
- confusion and error analysis
- reproducible split/config

### Week 2
Controlled Synthetic KB + retrieval:
- focused 8–12 intent RAG subset
- target 30–40 documents; scope-lock 24–30 if quality requires
- APPROVED/DRAFT/EXPIRED + version/effective date + hard negatives
- gold evidence mapping
- R0 approved-only retrieval vs R1 intent-aware approved-only retrieval

### Week 3
Grounded RAG + safety:
- answer only from approved evidence
- citation
- insufficient evidence → abstain/escalate
- critical eval set
- unsupported-answer and safe-resolution evidence
- R0 vs R1 and always-answer vs evidence-gated comparisons

### Week 4
Minimal service + incident:
- one end-to-end API endpoint
- structured response/logging
- model + KB/index version
- unit tests + at least one E2E regression
- one injected/reproduced KB regression with root cause, fix/rollback, regression test

### Week 5
Final evidence + system design:
- freeze versions
- final locked evaluation
- concise technical report
- 4–5 case demo
- one deep change-request design note

## Core invariants
1. DRAFT and EXPIRED documents never enter grounding context.
2. No approved supporting evidence → no factual answer.
3. Citations must refer to evidence that actually supports the claim.
4. Locked test/evaluation sets are not used for tuning.
5. Model/KB/index changes must not silently create safety regressions.
6. Important bugs become regression tests.

## Scope principle
`Depth of evidence > Breadth of features`

Do not turn this into a mini AI platform.
