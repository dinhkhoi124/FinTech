# Week 02 Summary

## P0 objective
Controlled Synthetic KB + gold evidence mapping + R0 vs R1 retrieval.

## Status
PASSED — W2-001 and W2-002 committed/pushed; W2-003 reviewed and accepted

## Deliverables completed
- [x] W2-001 controlled synthetic KB specification, generation, and validation.
- [x] W2-002 gold evidence mapping — Senior verdict `APPROVE_COMMIT`.
- [x] W2-003 controlled R0 vs R1 retrieval benchmark — final verdict `APPROVE_COMMIT`.

## Key evidence
| Claim | Evidence | Result | Decision |
|---|---|---|---|
| Controlled KB is valid and reproducible | `results/kb_v1_validation.json` and manifest | PASS; 36 docs, 26 eligible | Senior verdict `APPROVE_COMMIT`; freeze `kb_v1` |
| Lifecycle filtering is testable | Four complete version families | DRAFT/EXPIRED eligible count = 0 | Preserve fixed as-of date |
| Fine-grained scope is covered | `results/kb_v1_coverage.csv` | 10/10 intents have ≥2 eligible docs and ≥2 types | Do not add intents |
| Hard negatives are explicit | `configs/kb/hard_negative_matrix_v1.json` | 12 valid relationships | Use later for gold-design review only |
| Senior-review false-pass is closed | 29 focused tests + nine direct mutations | All former false-pass cases now fail; full suite 56/56 | Keep canonical KB bytes frozen |
| Gold mapping distributions are frozen | `results/gold_mapping_v1_validation.json` | PASS; 60 rows, 10/50 split, 50/10 response split | Await Senior/user review |
| Evidence roles cover lifecycle boundaries | manifest and coverage CSV | 26/26 eligible active; 10/10 ineligible forbidden | Preserve fixed as-of eligibility |
| Leakage controls are clean | overlap audit | zero query duplicates, KB candidates, and Banking77 equality overlaps | Keep query text frozen |
| Senior mapping-quality finding is corrected | correction ledger + manual review | 50/50 ANSWER direct-support audited; 19 gold roles changed; 10 safety probes replaced | Await final review |
| Residual v2 role inversion is patched | `Q_LOCK_CASH_PEND_002` | FAQ state section is gold; runbook recognition gate is acceptable | Preserve query/scenario/membership |
| Validator false-pass paths are closed | 43 focused tests + seven direct mutations | All pass/fail as expected; full suite 99/99 | Preserve scenario and hard-negative contracts |
| Retrieval corpus is frozen | `retrieval_corpus_manifest.json` | 26 documents / 52 chunks; no DRAFT/EXPIRED candidates | Reuse identical corpus for R0/R1 |
| Development-only boost selection | `retrieval_dev_selection.json` | λ=0.15; R0/R1 MRR@3 0.300000/0.400000 | Freeze before locked access |
| Locked strict retrieval | `retrieval_metrics.json` | R0/R1 MRR@3 0.483333/0.454167 | Retain R0 |
| Safety invariant | rankings + recomputed validator | all status and forbidden leakage = 0 | Gate passes |
| Reproducibility | `retrieval_version_manifest.json` | identical stable SHA across primary/rerun | Accept numerical reproducibility |
| Development rankings are auditable | `retrieval_dev_rankings.jsonl` | 50 rows; frozen metrics recompute exactly | λ remains 0.15 |
| Error and safety slices are separated | error CSV + safety diagnostics | 28 ANSWER / 10 safety rows | No retrieval-abstention claim |
| Multi-document diagnostic | `retrieval_multi_document_diagnostics.json` | 4 rows; mean Recall@3 0.666667; complete 1/4 for both | Diagnostic only |
| Error taxonomy is row-verifiable | error CSV + controlled fixtures | Automatic A/C/D/E/F/G/I = 3/4/4/4/2/4/7; reviewed = 3/4/4/4/2/3/8 | Await final re-review |
| Tracked and runtime verification | verifier + regression suites | PASS; 56 focused / 155 full tests | Numerical evidence unchanged |

## P0 exit criteria
See `docs/ROADMAP.md`.

## Risks / limitations
- Synthetic timelines are research controls, not real banking policy.
- Deterministic lexical near-duplicate screening does not prove absence of
  semantic overlap.
- Gold mapping has one construction reviewer and is not independent annotation.
- The soft intent boost improved development results but regressed strict locked
  MRR@3, Hit@1, Recall@3, and complete coverage.
- Classifier accuracy on 60 synthetic mapping queries is 0.55 diagnostic only;
  its probabilities are uncalibrated.
- The initial error analysis incorrectly treated empty-gold safety probes as
  retrieval misses; corrected evidence supersedes the 38-row analysis.
- Six rows were falsely categorized F because strict gold could satisfy the
  sibling predicate and D omitted retained retrieval success; the rank-aware
  taxonomy and per-row verifier supersede those labels.
- The dependency-free custom schema mirror must remain synchronized with its JSON
  Schema artifact; focused mutation tests are the regression control.

## Handoff
- Senior review verdict for W2-001: `APPROVE_COMMIT`.
- Week 2 P0 gate is `PASSED`.
- W2-002 review history: initial construction review → `FIX_REQUIRED` →
  direct-support/safety correction → validator hardening → residual one-row
  inversion → final patch → `APPROVE_COMMIT`.
- W2-002 is DONE / REVIEWED / COMMITTED / PUSHED.
- W2-003 review history: initial completion → Senior `FIX_REQUIRED` for
  safety/error slicing and tracked verification → dev-ranking/verifier correction
  → Senior taxonomy `FIX_REQUIRED` → rank-aware taxonomy patch → final
  `APPROVE_COMMIT`.
- W2-003 is DONE / REVIEWED / ACCEPTED; accepted locked results retain R0 and
  Week 3 is NOT STARTED.
