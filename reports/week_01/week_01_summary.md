# Week 01 Summary

## P0 objective
Full Banking77 + exactly two baselines + reproducible evaluation + error analysis.

## Status
`PASSED` — W1-001 through W1-004 complete; Week 2 not started

## Final benchmark

Both frozen candidates were refit on the same 10,003 non-test samples and evaluated
on the untouched 3,080-row official test.

| Model | Accuracy | Macro-F1 | Correct | Errors | Dimension | Repro-run total |
|---|---:|---:|---:|---:|---:|---:|
| TF-IDF unigram + LR | 0.878247 | 0.878362 | 2,705 | 375 | 2,320 | 4.259 s |
| frozen MiniLM + LR | 0.908117 | 0.908075 | 2,797 | 283 | 384 | 92.227 s |

Semantic minus lexical: accuracy `+0.029870`; macro-F1 `+0.029713`.

## Key evidence and decisions

- Authoritative PolyAI data remains pinned to commit `57ec275...` and protocol
  membership SHA-256 `baa3d31f...c902`.
- Evaluation protocol was preregistered before test access; both frozen candidates
  used identical final-fit scope and no test-driven tuning.
- Paired outcomes: 2,611 both correct, 94 lexical-only, 186 semantic-only, and
  189 both wrong.
- Semantic improved 49 class F1 values, regressed 21, and left 7 unchanged.
- Thirty deterministic error/disagreement cases were reviewed. Ambiguous label
  boundaries were most common; transaction-state and product-rail confusions remain.
- Both models were correct on all seven normalized-overlap rows. Exclusion changes
  each aggregate metric by less than 0.0003, so the recommendation is insensitive.
- Confidence distributions are diagnostic only; no calibration/threshold was fitted.
- Primary and independent fresh-cache reruns matched all stable artifacts.
- Frozen MiniLM semantic baseline is selected downstream; lexical is fallback.

## Runtime trade-off

Lexical is about 20× faster for the full measured CPU final-fit/evaluation and has
no encoder cache. Semantic requires ~183 MB local encoder cache and ~21 MB embedding
cache, but its broad ~2.97 percentage-point aggregate gain satisfies the
preregistered clear-gain rule. These are local CPU experiment timings, not
production latency claims.

## P0 exit criteria
- [x] W1-001 data audit and deterministic locked split.
- [x] W1-002 lexical baseline frozen without test tuning.
- [x] W1-003 semantic baseline frozen without test tuning.
- [x] W1-004 fair official-test evaluation of exactly two candidates.
- [x] Accuracy, macro-F1, all-class metrics, predictions, and confusions.
- [x] Paired, confidence, overlap, runtime, and bounded manual error analysis.
- [x] Reproducibility and public-safety evidence.
- [x] Downstream candidate selected and frozen.
- [x] Week 1 P0 gate passed.

## Limitations
- Seven normalized official-boundary overlaps are retained and disclosed.
- Some Banking77 queries are underspecified or appear inconsistent with fine-grained
  labels; hypotheses are not treated as proven annotation errors.
- No calibration, abstention, OOS/OOD, third model, or fine-tuning was performed.
- Semantic inference cost must be revisited when a real service latency target exists.

## Handoff
Week 1 is closed. Queue Week 2 only; do not implement it without separate user
authorization. Carry exact semantic revision/config as the selected intent model
and retain lexical unigram as the reproducible fallback.
