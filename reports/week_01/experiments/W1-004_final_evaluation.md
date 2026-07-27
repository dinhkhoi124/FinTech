# W1-004 — Final Locked Test Evaluation and Week 1 Gate

## Verdict

`PASS`. Both frozen baselines were refit once per run on all 10,003 official
training samples and evaluated on the 3,080-row official test under the
preregistered protocol. Semantic MiniLM is selected for downstream use; the
lexical unigram model remains the fallback. No test-driven tuning occurred.

## Pre-test gate and preregistration

- Git HEAD and `origin/main`: `5f287a18a50ec073f961290962de003e1f4e38bc`.
- W1-001/W1-002/W1-003 commits and frozen manifests verified.
- Protocol: `banking77_w1_v1`; membership SHA-256 `baa3d31f...c902`.
- Prior state: `test_encoded=false`, `test_evaluated=false`; no prior test artifacts.
- Evaluation config created before test access with SHA-256
  `a6ac09654884528aa6ccabf784a349304eddecb3ccb0add680000ad4f6272a40`.
- An initially typed full Git SHA was corrected before test access. The gate caught
  the mismatch; no test artifact existed and no score had been observed.

The preregistered final-fit protocol was identical for both candidates:

```text
locked train 8,998 + locked validation 1,005
→ 10,003 samples ordered by stable sample ID
→ refit each frozen configuration once
→ evaluate on 3,080 official-test samples ordered by stable sample ID
```

## Official benchmark

| Model | Representation | Accuracy | Macro-F1 | Correct | Errors | Dimension | Repro-run total |
|---|---|---:|---:|---:|---:|---:|---:|
| Lexical | TF-IDF word unigram | 0.878247 | 0.878362 | 2,705 | 375 | 2,320 | 4.259 s |
| Semantic | normalized frozen MiniLM | 0.908117 | 0.908075 | 2,797 | 283 | 384 | 92.227 s |

Semantic minus lexical: accuracy `+0.029870`; macro-F1 `+0.029713`.

Validation-to-test changes were positive for both models:

- lexical: accuracy `+0.012575`, macro-F1 `+0.015713`;
- semantic: accuracy `+0.007619`, macro-F1 `+0.010054`.

These values are not used for retuning.

## Paired outcomes

| Outcome | Count |
|---|---:|
| Both correct | 2,611 |
| Lexical correct / semantic wrong | 94 |
| Lexical wrong / semantic correct | 186 |
| Both wrong | 189 |

Semantic corrected 186 lexical errors while introducing 94 regressions, a net
gain of 92 correct predictions. The gain is broad: semantic F1 improved for 49
intents, regressed for 21, and was unchanged for 7. No semantic class regression
reached the preregistered absolute F1 threshold of 0.20.

Largest F1 improvements included `virtual_card_not_working` (+0.244821),
`card_not_working` (+0.162494), `why_verify_identity` (+0.153333), and
`verify_my_identity` (+0.149498). Largest regressions included
`declined_transfer` (-0.092515), `direct_debit_payment_not_recognised`
(-0.049787), `beneficiary_not_allowed` (-0.048583), and
`reverted_card_payment?` (-0.047414).

Validation findings did not all persist: `cancel_transfer` improved by 0.025610
on test; `top_up_reverted` improved by 0.082621; `pending_top_up` regressed by
0.032843; `request_refund` improved by 0.062657; and
`reverted_card_payment?` regressed by 0.047414.

## Confusions and bounded manual review

Semantic reduced several prominent directional confusions:

- `why_verify_identity → verify_my_identity`: 9 → 3;
- `virtual_card_not_working → get_disposable_virtual_card`: 8 → 1;
- `request_refund → Refund_not_showing_up`: 5 → 0;
- `top_up_reverted → top_up_failed`: 5 → 2.

It worsened `declined_transfer → declined_card_payment` from 2 → 6 and retained
fine-grained boundaries around transfer timing, direct debit/card recognition,
disposable cards, and transaction states.

The deterministic 30-row review contains semantic fixes, lexical-only correct
cases, both-wrong cases, high-confidence errors, low-margin errors, and short
queries. Taxonomy counts were T1=1, T2=5, T3=4, T4=3, T5=10, T6=2, T7=5.
Root-cause statements are hypotheses. The most common reviewed issue was ambiguous
or underspecified label boundaries, followed by transaction-state and product-rail
confusion. Five cases warrant potential annotation/taxonomy review; they are not
silently relabeled.

## Confidence diagnostics

Probabilities are diagnostic only and are not assumed calibrated.

- Lexical mean max probability: correct `0.5473`, incorrect `0.2374`.
- Semantic mean max probability: correct `0.6807`, incorrect `0.3422`.
- Lexical mean top-1/top-2 margin: correct `0.4769`, incorrect `0.1092`.
- Semantic mean top-1/top-2 margin: correct `0.5978`, incorrect `0.1694`.

Correct and incorrect distributions separate directionally, but confidently wrong
examples remain. No threshold, calibration, abstention, or OOS policy was fitted.

## Normalized-overlap sensitivity

Both models correctly classified all seven W1-001 normalized-overlap test rows.
Excluding only those evidenced rows yields 3,073 samples:

| Model | Accuracy excluding overlap | Macro-F1 excluding overlap | Accuracy change | Macro-F1 change |
|---|---:|---:|---:|---:|
| Lexical | 0.877969 | 0.878073 | -0.000277 | -0.000289 |
| Semantic | 0.907908 | 0.907874 | -0.000209 | -0.000201 |

The semantic recommendation does not materially depend on these seven rows. The
canonical benchmark remains the unmodified 3,080-row official test.

## Runtime and complexity

Primary/repro total evaluation times were 108.906/97.536 seconds. Per-model totals:

- lexical: 4.587/4.259 seconds; 2,320 features; portable model 1,666,588 bytes;
- semantic: 103.186/92.227 seconds; 384 dimensions; portable classifier 284,058
  bytes; local encoder cache 183,156,831 bytes; embedding cache 21,038,649 bytes.

Semantic is materially slower and requires model/cache storage, but its ~2.97
percentage-point aggregate gain and broad class improvements justify the added
complexity for this research prototype. These CPU measurements are not production
latency claims.

## Reproducibility and decision

Primary and independent fresh-cache reruns produced byte-identical classifier
parameters, predictions, metrics, per-class scores, confusions, paired rows,
confidence analysis, overlap analysis, and manual-review candidate selection.
Runtime-bearing benchmark/runtime artifacts differ as expected.

The preregistered `semantic_clear_gain` branch applies: macro-F1 improved by more
than 0.01, accuracy did not decrease, results reproduced, and there was no
per-class regression of at least 0.20. Selected candidate:

`semantic_all_minilm_l6_v2` using config SHA-256 `de4ebff8...7b50b`.

Fallback: `lexical_word_unigram`. Both remain frozen; no third model is opened.

## Week 1 P0 gate

`PASS`: W1-001 through W1-004 are complete; both frozen candidates were evaluated
fairly; required artifacts, error analysis, overlap limitation, recommendation,
tests, reproducibility, and public-safety evidence are present. Week 2 is queued
but was not started by this task.

Final verification: isolated W1-004 7/7, lexical 3/3, semantic 4/4, and full
repository suite 27/27 passed under the locked semantic environment. Banking77
artifact verification, semantic contract verification, and W1-004 result
verification also passed.
