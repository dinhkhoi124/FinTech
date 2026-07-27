# Week 01 Summary

## P0 objective
Full Banking77 + 2 baselines + reproducible evaluation + error analysis.

## Status
IN PROGRESS — W1-001, W1-002, and W1-003 complete; W1-004 not started

## Deliverables completed
- Authoritative Banking77 acquisition, audit, and deterministic locked protocol.
- Controlled TF-IDF + Logistic Regression lexical validation baseline.
- One controlled frozen-encoder semantic validation baseline using the same sample
  IDs, labels, metric implementation, and Logistic Regression family.
- Reproducible semantic CLI, exact model/dependency provenance, aligned evidence,
  ignored cache/model artifacts, and an independent fresh-cache rerun.

## Key evidence
| Claim | Evidence | Result | Decision |
|---|---|---|---|
| Authoritative data is pinned | `data/banking77_source_manifest.json` | PolyAI commit `57ec275...`, 3 files with SHA-256 | Reject silent mirrors/repackages |
| Split is reproducible and test frozen | `data/banking77_split_manifest.json` | 8,998 / 1,005 / 3,080; membership `baa3d31f...c902` | Tune only on validation |
| Lexical baseline is frozen | `lexical_validation_metrics.json` | Accuracy 0.865672, macro-F1 0.862649 | Carry unchanged to W1-004 |
| Semantic baseline is frozen | `semantic_validation_metrics.json` | Accuracy 0.900498, macro-F1 0.898020 | Carry unchanged to W1-004 |
| Semantic comparison is controlled | `semantic_lexical_validation_comparison.json` | Accuracy +0.034826; macro-F1 +0.035371 | H1 supported on validation only |
| Semantic artifacts reproduce | `semantic_baseline_manifest.json` and experiment note | Eight stable evidence/model hashes matched across fresh-cache reruns | Retain exact revision/config |
| Frozen test remains untouched | semantic manifests | `test_encoded=false`, `test_evaluated=false` | W1-004 exclusively owns test |

## Important findings
- No missing/empty text or label, invalid label, exact duplicate, exact conflicting
  label, or exact official train/test overlap was found in W1-001.
- Seven normalized official-boundary overlaps are label-consistent and retained as
  a known evaluation limitation; the official boundary was not changed.
- The semantic baseline improved 43 per-class validation F1 values, regressed 14,
  and left 20 unchanged versus lexical; only one regression reached the
  predeclared absolute material threshold of 0.10 (`cancel_transfer`, -0.125).
- Three of four predeclared lexical focus confusion counts decreased; the
  `top_up_reverted → top_up_failed` count remained 3.
- These per-class and confusion findings are validation diagnostics only because
  class support is 4–19 and the official test remains unseen.
- Primary and independent fresh-cache semantic runs took 79.315 s and 70.651 s on
  CPU; downloaded encoder and embedding/model caches remain ignored.

## P0 exit criteria
- [x] W1-001 data audit and deterministic locked split.
- [x] W1-002 lexical baseline (validation selection complete; test reserved for W1-004).
- [x] W1-003 semantic baseline (validation selection complete; test reserved for W1-004).
- [ ] W1-004 evaluation, confusion/error analysis, and Week 1 gate.

## Risks / limitations
- Both reported baseline numbers are validation diagnostics, not official test claims.
- Validation per-class deltas are directional due to low class support.
- Cold-cache semantic reproduction depends on availability of the exact upstream
  model revision; all required provenance and snapshot checksums are recorded.
- The Week 1 P0 gate remains open until W1-004 completes.

## Handoff
- Stop for review. If separately authorized, W1-004 must first verify the locked
  data and both frozen baseline configurations, then evaluate exactly those two
  approaches once on the untouched official test.
- Do not start a third model, P1, or Week 2.
