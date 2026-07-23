# Week 01 Summary

## P0 objective
Full Banking77 + 2 baselines + reproducible evaluation + error analysis.

## Status
IN PROGRESS — W1-001 and W1-002 complete; W1-003/W1-004 not started

## Deliverables completed
- W1-001 authoritative Banking77 acquisition/provenance contract.
- Deterministic official-train → train/validation membership with frozen official test.
- Data integrity/class-distribution/leakage/short-query audit.
- Reproducibility CLI, manifest verification, and regression tests.
- Controlled TF-IDF + Logistic Regression lexical baseline selected on locked
  validation only; portable fitted parameters and aligned evidence retained.

## Key evidence
| Claim | Evidence | Result | Decision |
|---|---|---|---|
| Authoritative data is pinned | `data/banking77_source_manifest.json` | PolyAI commit `57ec275...`, 3 files with SHA-256, CC-BY-4.0 | Reject silent mirrors/repackages |
| Full Banking77 foundation is present | `reports/week_01/results/banking77_data_audit.json` | 13,083 samples, 77 intents | Use full taxonomy for Week 1 |
| Test remains frozen | `data/banking77_split_manifest.json` | 8,998 train / 1,005 validation / 3,080 test | Tune only on validation |
| Split is reproducible | W1-001 `verify` output and manifest | Combined membership SHA-256 `baa3d31f...c902`; rerun matches | Require same manifest in W1-002/W1-003 |
| Leakage risk is visible | W1-001 audit note | 0 exact overlap; 7 normalized label-consistent overlaps | Preserve official source; slice in W1-004 |
| Lexical baseline is frozen | `reports/week_01/results/lexical_validation_metrics.json` | Unigram accuracy 0.865672, macro-F1 0.862649 on 1,005 validation rows | Carry selected config to W1-004; do not claim test performance |
| Lexical artifacts reproduce | `reports/week_01/results/lexical_baseline_manifest.json` | Six model/evidence hashes matched across consecutive runs | Use canonical fitted parameters and fixed numerical threads |

## Important data findings

- No missing/empty text or label, invalid label, exact duplicate, exact conflicting
  label, or exact official train/test overlap was found.
- Official train is imbalanced (35–187 examples per intent); official test has 40
  examples per intent.
- Validation contains every intent with 4–19 examples per intent.
- Short inputs exist: 9 examples have at most 2 tokens and 49 have at most 3.
- Uni+bigrams underperformed unigrams on validation (macro-F1 0.846269 vs
  0.862649) while creating 22,225 vs 2,237 features.
- The selected unigram model made 135 validation errors. Frequent confusions
  separated payment rails or pending/reverted/failed transaction states.

## P0 exit criteria
- [x] W1-001 data audit and deterministic locked split.
- [x] W1-002 lexical baseline (validation selection complete; test reserved for W1-004).
- [ ] W1-003 semantic/model-based baseline.
- [ ] W1-004 evaluation, confusion/error analysis, and Week 1 gate.

## Risks / limitations
- Seven normalized official-boundary overlaps are a known evaluation limitation.
- W1-002 numbers are validation diagnostics, not official test claims.
- Some validation classes have only 4–19 examples, so per-class results remain
  directional until the frozen-test evaluation.
- The Week 1 P0 gate remains open until W1-003 and W1-004 complete.

## Handoff
- Queue W1-003 only. It must consume `banking77_w1_v1` unchanged and use the same
  validation/evaluation contract.
- Do not start W1-003 or inspect frozen-test outcomes without separate authorization.
