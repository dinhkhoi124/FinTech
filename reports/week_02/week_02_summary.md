# Week 02 Summary

## P0 objective
Controlled Synthetic KB + gold evidence mapping + R0 vs R1 retrieval.

## Status
IN PROGRESS — W2-001 DONE / REVIEWED / COMMITTED / PUSHED; W2-002 DONE / REVIEWED / ACCEPTED; W2-003 queued, not started

## Deliverables completed
- [x] W2-001 controlled synthetic KB specification, generation, and validation.
- [x] W2-002 gold evidence mapping — Senior verdict `APPROVE_COMMIT`.
- [ ] W2-003 controlled R0 vs R1 retrieval benchmark.

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

## P0 exit criteria
See `docs/ROADMAP.md`.

## Risks / limitations
- Synthetic timelines are research controls, not real banking policy.
- Deterministic lexical near-duplicate screening does not prove absence of
  semantic overlap.
- Gold mapping has one construction reviewer and is not independent annotation.
- Retrieval quality remains unmeasured by design.
- The dependency-free custom schema mirror must remain synchronized with its JSON
  Schema artifact; focused mutation tests are the regression control.

## Handoff
- Senior review verdict for W2-001: `APPROVE_COMMIT`.
- Week 2 P0 remains in progress.
- W2-002 review history: initial construction review → `FIX_REQUIRED` →
  direct-support/safety correction → validator hardening → residual one-row
  inversion → final patch → `APPROVE_COMMIT`.
- W2-002 is DONE / REVIEWED / ACCEPTED. W2-003 is queued but not started.
- W2-003 remains TODO / NOT STARTED.
