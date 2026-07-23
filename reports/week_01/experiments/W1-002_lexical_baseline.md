# W1-002 — Controlled Lexical Baseline

## Objective and scope

Establish one simple lexical reference using TF-IDF + Logistic Regression on the
locked `banking77_w1_v1` development protocol. This task performs model selection
only on validation. It does not load, predict, or evaluate the 3,080-row frozen
official test set; that single controlled evaluation is reserved for W1-004.

## Inputs and invariants

- Authoritative source revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`.
- Locked membership: 8,998 train / 1,005 validation / 3,080 frozen test.
- Combined membership SHA-256:
  `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`.
- Runtime: CPython 3.11.9 with exact pins in
  `requirements/week1-lexical.txt`.
- Classifier, seed, solver, and all settings except `ngram_range` were held fixed.
- Selection metric was validation macro-F1; accuracy and candidate ID were fixed
  tie-breakers.

## Controlled candidates

| Candidate | Word n-grams | Features | Validation accuracy | Validation macro-F1 |
|---|---:|---:|---:|---:|
| `word_unigram` | 1–1 | 2,237 | 0.865672 | 0.862649 |
| `word_unigram_bigram` | 1–2 | 22,225 | 0.857711 | 0.846269 |

Both candidates used lowercase text, `min_df=1`, sublinear TF, LogisticRegression
with `C=1.0`, `solver=lbfgs`, `max_iter=1000`, seed `20260723`, and a fixed
single-thread numerical execution policy.

## Decision

Freeze `word_unigram` for the later W1-004 comparison. It improved validation
macro-F1 by 0.016381 and accuracy by 0.007960 while using about one tenth as many
features. No additional lexical sweep or third model was opened.

## Minimal validation error inspection

The selected model made 135 errors among 1,005 validation examples. The most
frequent directional confusion pairs (three cases each) were:

- `direct_debit_payment_not_recognised` → `card_payment_not_recognised`;
- `pending_top_up` → `top_up_failed`;
- `reverted_card_payment?` → `request_refund`;
- `top_up_reverted` → `top_up_failed`.

Representative stable sample IDs reviewed included
`10c97cc5...216d1d5` (unrecognized payment without a strong payment-rail cue),
`10414657...b540110` (top-up “didn't finish”), and
`5450a431...2ed638` (transfer timing vs pending transfer). The evidence supports
a lexical limitation: neighboring intents often share transaction nouns while
the decisive distinction is event state, rail, or temporal semantics. This is a
W1-002 observation only, not the final W1-004 taxonomy or gate decision.

Lowest selected per-class F1 values were `card_acceptance` (0.545455),
`card_not_working` (0.571429), `topping_up_by_card` (0.666667), and
`virtual_card_not_working` (0.666667). Per-class support is retained in the CSV;
small validation support means these values are diagnostic, not final test claims.

## Reproducibility and artifact decision

Exact command:

```powershell
py -3.11 scripts/baselines/lexical.py --root . --config configs/models/banking77_lexical_w1.json --inspect-errors 20
```

Two consecutive independent runs produced byte-identical metrics, predictions,
per-class metrics, confusions, portable model parameters, and manifest. The model
uses canonical JSON + deterministic gzip rather than joblib serialization because
joblib bytes varied across processes despite identical predictions/metrics. The
portable artifact records vocabulary, IDF, class order, coefficients, and
intercepts and remains ignored under `artifacts/`; its SHA-256 is
`4f564e227c5f61164d51710b1a86c6e8405fa0a793cf5b71b9842f0b40d5b021`.

## Evidence

- Config: `configs/models/banking77_lexical_w1.json`.
- Metrics: `reports/week_01/results/lexical_validation_metrics.json`.
- Per-class metrics: `reports/week_01/results/lexical_validation_per_class.csv`.
- Predictions: `reports/week_01/results/lexical_validation_predictions.csv`.
- Confusion counts: `reports/week_01/results/lexical_validation_confusions.csv`.
- Version/hashes: `reports/week_01/results/lexical_baseline_manifest.json`.
- Tests: 15/15 passed after adding W1-002 coverage.

## Limitations and next boundary

- These are validation results, not official test results.
- The two-candidate comparison isolates only word bigrams; it is not a broad
  hyperparameter search.
- W1-003 has not started. W1-004 must later evaluate exactly the two frozen
  baselines once on the untouched official test and perform the final analysis.
