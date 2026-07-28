# Week 02 Summary

## P0 objective
Controlled Synthetic KB + gold evidence mapping + R0 vs R1 retrieval.

## Status
IN PROGRESS — W2-001 DONE / REVIEWED / ACCEPTED; W2-002 and W2-003 not started

## Deliverables completed
- [x] W2-001 controlled synthetic KB specification, generation, and validation.
- [ ] W2-002 gold evidence mapping.
- [ ] W2-003 controlled R0 vs R1 retrieval benchmark.

## Key evidence
| Claim | Evidence | Result | Decision |
|---|---|---|---|
| Controlled KB is valid and reproducible | `results/kb_v1_validation.json` and manifest | PASS; 36 docs, 26 eligible | Senior verdict `APPROVE_COMMIT`; freeze `kb_v1` |
| Lifecycle filtering is testable | Four complete version families | DRAFT/EXPIRED eligible count = 0 | Preserve fixed as-of date |
| Fine-grained scope is covered | `results/kb_v1_coverage.csv` | 10/10 intents have ≥2 eligible docs and ≥2 types | Do not add intents |
| Hard negatives are explicit | `configs/kb/hard_negative_matrix_v1.json` | 12 valid relationships | Use later for gold-design review only |
| Senior-review false-pass is closed | 29 focused tests + nine direct mutations | All former false-pass cases now fail; full suite 56/56 | Keep canonical KB bytes frozen |

## P0 exit criteria
See `docs/ROADMAP.md`.

## Risks / limitations
- Synthetic timelines are research controls, not real banking policy.
- Deterministic lexical near-duplicate screening does not prove absence of
  semantic overlap.
- Gold mapping and retrieval quality remain unmeasured by design.
- The dependency-free custom schema mirror must remain synchronized with its JSON
  Schema artifact; focused mutation tests are the regression control.

## Handoff
- Senior review verdict for W2-001: `APPROVE_COMMIT`.
- Week 2 P0 remains in progress.
- W2-002 requires a separate reviewed task contract; W2-003 remains not started.
