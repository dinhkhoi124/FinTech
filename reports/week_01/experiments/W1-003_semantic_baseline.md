# W1-003 — Frozen Semantic Representation Baseline

## Objective and hypothesis

Test whether one pretrained dense semantic representation improves fine-grained
Banking77 intent classification over the frozen lexical reference, especially
when surface vocabulary is shared but transaction state, payment rail, or
operational meaning differs.

This is a controlled representation comparison:

```text
W1-002: TF-IDF word unigrams → Logistic Regression
W1-003: frozen all-MiniLM-L6-v2 embeddings → Logistic Regression
```

The downstream classifier remains `C=1.0`, `lbfgs`, `max_iter=1000`, seed
`20260723`, and one numerical thread. No model/config search was performed.

## Frozen contracts

- Data protocol: `banking77_w1_v1`.
- Train/validation/frozen test: 8,998 / 1,005 / 3,080.
- Membership SHA-256:
  `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`.
- Lexical config SHA-256:
  `f99955a401063fa849d93af2dec3639e8e3aaa3f8a99d3029b0ce01edb02b64d`.
- Frozen test encoded/evaluated: no/no.

The semantic loader reuses W1-002's locked train/validation loader and metric
functions. It does not reference a test example or create a test cache.

## Encoder provenance and configuration

- Model ID: `sentence-transformers/all-MiniLM-L6-v2`.
- Exact Hugging Face revision:
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- License recorded from upstream metadata: Apache-2.0.
- Encoder frozen: yes; all parameters have `requires_grad=false` and eval mode.
- Pooling: mean.
- Output dimension: 384.
- Sentence Transformer/tokenizer maximum sequence length: 256.
- Embedding normalization: L2 normalization enabled, predeclared before run.
- Batch size: 64.
- Device: CPU; CUDA unavailable.
- Remote code: not trusted/executed.

The local snapshot contained 11 required files totaling 91,578,415 bytes. The
90,868,376-byte `model.safetensors` SHA-256 is
`53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`.
Weights remain under ignored `artifacts/`; only provenance and checksums are
trackable.

## Executions

1. Contract tests with a deterministic fake encoder.
2. Realistic smoke test: 16 train / 4 validation rows across four classes;
   embeddings `(16,384)` and `(4,384)`; four predictions; no metric used as final
   evidence.
3. One full primary run with the predeclared configuration.
4. One independent full refresh rerun of the same configuration.
5. Cache verification and limited validation-only error inspection.

No alternative encoder, normalization, pooling, `C`, or classifier was tried.

## Validation results

| Baseline | Accuracy | Macro-F1 | Correct | Errors |
|---|---:|---:|---:|---:|
| Frozen lexical unigram | 0.865672 | 0.862649 | 870 | 135 |
| Frozen semantic encoder | 0.900498 | 0.898020 | 905 | 100 |
| Semantic − lexical | +0.034826 | +0.035371 | +35 | −35 |

These are validation results only. They do not establish a frozen-test winner.

## Per-class and confusion findings

Using strict F1 change relative to lexical:

- 43 classes improved;
- 14 regressed;
- 20 were unchanged;
- 14 improved by at least 0.10 F1;
- one regressed by at least 0.10 F1 (`cancel_transfer`, −0.125).

Largest improvements included `virtual_card_not_working` (+0.1905, support 4),
`top_up_by_card_charge` (+0.1739, support 11),
`declined_cash_withdrawal` (+0.1606, support 17), and
`balance_not_updated_after_bank_transfer` (+0.1444, support 17). Small support,
especially four rows, makes these diagnostic rather than final claims.

Largest regressions included `cancel_transfer` (−0.125),
`wrong_amount_of_cash_received` (−0.100 within floating representation),
`card_about_to_expire` (−0.080), and `compromised_card` (−0.0743).

For the four W1-002 focus confusions:

| True → predicted | Lexical | Semantic | Change |
|---|---:|---:|---:|
| direct debit unrecognized → card payment unrecognized | 3 | 2 | −1 |
| pending top-up → top-up failed | 3 | 2 | −1 |
| reverted card payment → request refund | 3 | 0 | −3 |
| top-up reverted → top-up failed | 3 | 3 | 0 |

Semantic representation reduced three focus pairs but did not solve reverted vs
failed top-up. It also created new two-case patterns such as
`cancel_transfer → terminate_account`, `card_about_to_expire → order_physical_card`,
and `reverted_card_payment? → Refund_not_showing_up`. These examples suggest the
encoder can improve operational semantics overall while still collapsing intents
whose short wording omits the decisive event/state cue.

## Runtime and cache evidence

Primary CPU run:

- Model load: 8.79 seconds.
- Train encoding: 58.89 seconds for 8,998 rows.
- Validation encoding: 8.24 seconds for 1,005 rows.
- Classifier fit: 2.65 seconds.
- Validation prediction: 0.024 seconds.
- Total experiment: 79.31 seconds.
- Embedding cache: 16,086,001 bytes.
- Hugging Face cache: 183,156,831 bytes; required snapshot footprint was
  91,578,415 bytes, with cache metadata/blob duplication accounting for the
  larger on-disk cache directory.

These are local experiment timings, not production latency. Compared with the
2,237-dimensional sparse lexical representation, semantic uses 384 dense values
per query but adds pretrained model loading/encoding complexity.

## Cache and reproducibility

Cache key:
`c7e89e194c319cb4217a91302a663058773f494d5bc51e8261a8900832d09302`.

- Train embedding shape/hash: `(8998,384)`,
  `ffa3572d9c24940fe72466ab1ce42599e88ff7cdf9e897c32509bbb5249be0b6`.
- Validation embedding shape/hash: `(1005,384)`,
  `c2c717f087f0b6896ce4d68e2144f58c60b9f558e1985b19568c0ee2b7422048`.
- Train/validation sample-ID hashes were independently verified.
- Both primary and reproducibility runs forced fresh encoding (`cache_hit=false`).
- Eight stable artifacts were byte-identical across independent refresh runs:
  classifier parameters, metrics, per-class metrics, predictions, confusions,
  embedding manifest, model provenance, and lexical comparison.
- Runtime and overall manifest bytes intentionally differ because measured timing
  and run-label evidence differ; this is not numerical nondeterminism.

## Debugging evidence

The first full test run exposed an integration-fixture bug: Git provenance assumed
every supplied repository root contained `.git`. The full project run was valid,
but the isolated temp-root test failed. The helper now records
`{"available": false}` outside Git and continues to record HEAD/dirty state in the
real repository. The previously failing integration test is the regression guard.

Hugging Face also reported that optional Xet acceleration was absent and used its
regular HTTP fallback. No new dependency was added because correctness and exact
revision acquisition succeeded without it.

Pre-commit verification on 2026-07-27 ran the semantic test module in isolation
with `.venv-semantic` before the full suite. Direct imports resolved from
`src/payresolve_ai`; the isolated module passed 4/4 tests and the same interpreter
then passed the full 20/20 tests. This confirms the semantic tests do not depend on
another test mutating `sys.path` first.

## Decision and boundary

Freeze this semantic configuration for W1-004. Validation supports H1, but the
official test performance remains unknown. Do not retune either baseline, start a
third model, or perform the final cross-model/frozen-test decision within W1-003.

## Evidence

- Config: `configs/models/banking77_semantic_w1.json`.
- Dependency lock: `requirements/week1-semantic.txt`.
- Model provenance: `reports/week_01/results/semantic_model_provenance.json`.
- Embedding manifest: `reports/week_01/results/semantic_embedding_manifest.json`.
- Metrics/predictions/per-class/confusions: `reports/week_01/results/semantic_validation_*`.
- Lexical comparison: `reports/week_01/results/semantic_lexical_validation_comparison.json`.
- Runtime: `reports/week_01/results/semantic_runtime.json`.
- Frozen result manifest: `reports/week_01/results/semantic_baseline_manifest.json`.
