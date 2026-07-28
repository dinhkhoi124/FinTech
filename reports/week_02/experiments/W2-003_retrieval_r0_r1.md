# W2-003 — Controlled R0 vs R1 Retrieval Benchmark

## Question and preregistered comparison

Does the frozen predicted Banking77 intent improve approved-evidence ranking when
used only as `cosine + lambda * intent_scope_match`? R0 is exact dense cosine;
R1 differs only by this soft term. No hard filtering, confidence routing,
query expansion, reranker, second encoder, or locked-set tuning is used.

## Frozen setup

- KB/mapping: reviewed `kb_v1` and `gold_mapping_v1` hashes.
- Corpus: 26 eligible documents, 52 deterministic section chunks.
- Encoder: normalized 384D `all-MiniLM-L6-v2`, revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU.
- Classifier: W1-004 `semantic_all_minilm_l6_v2` portable final-fit parameters;
  10,003 non-test training rows; confidence diagnostic only.
- Top-k: 3. Primary relevance is `gold_evidence_ids` only.

## Development selection

| λ | Strict Hit@1 | Strict Recall@3 | Strict MRR@3 | Complete@3 |
|---:|---:|---:|---:|---:|
| R0 | 0.200000 | 0.500000 | 0.300000 | 0.500000 |
| 0.05 | 0.200000 | 0.600000 | 0.333333 | 0.600000 |
| 0.10 | 0.200000 | 0.600000 | 0.333333 | 0.600000 |
| 0.15 | 0.200000 | 0.800000 | 0.400000 | 0.800000 |
| 0.20 | 0.200000 | 0.800000 | 0.400000 | 0.800000 |

λ=0.15 was frozen because 0.15 and 0.20 tied on MRR, Hit@1, and Recall@3;
the preregistered lower-lambda tie-break applies.

The post-review `audit-dev-selection` command reproduced and persisted 50
canonical ranking rows (10 queries × R0 plus four positive-lambda variants).
Tracked verification recomputes every grid metric from those rows; it does not
select a new lambda.

## Locked results

| Metric (40 ANSWER queries) | R0 | R1 | R1 − R0 |
|---|---:|---:|---:|
| Strict Hit@1 | 0.350000 | 0.325000 | -0.025000 |
| Strict Recall@3 | 0.616667 | 0.566667 | -0.050000 |
| Strict MRR@3 | 0.483333 | 0.454167 | -0.029167 |
| Complete Gold Coverage@3 | 0.575000 | 0.525000 | -0.050000 |
| Relaxed Hit@1 | 0.375000 | 0.450000 | +0.075000 |
| Relaxed Hit@3 | 0.775000 | 0.675000 | -0.100000 |

R1 produced 3 WIN / 4 LOSS / 33 TIE first-gold outcomes. Both top-1 were correct
for 13 queries and incorrect for 26; R1 broke one R0 top-1 success and corrected
none. All DRAFT, EXPIRED, wrong-status, and forbidden-evidence leakage rates were
zero. The 28-row ANSWER error analysis and ten-row safety diagnostic slice are
separate. Safety-query rankings are diagnostics only and do not claim abstention.

For the four contract-level multi-document queries, both R0 and R1 have mean
gold Recall@3 0.666667 and complete coverage 1/4 (0.25). This diagnostic does not
change the primary decision.

Senior final review verdict is `APPROVE_COMMIT`. The complete review lifecycle
was initial completion → safety/error-slicing and tracked-verifier
`FIX_REQUIRED` → dev-ranking/verifier correction → taxonomy `FIX_REQUIRED` →
rank-aware taxonomy patch → final approval. W2-003 is DONE / REVIEWED / ACCEPTED,
the Week 2 P0 gate is PASSED, R0 remains selected, and Week 3 is NOT STARTED.

## Decision

Retain R0. R1 lost the frozen primary metric and also regressed both strict
tie-break metrics. Its relaxed Hit@1 gain cannot overturn that strict loss.
Primary and reproducibility artifacts matched exactly; runtime differences are
observational only.

## Evidence-verifier correction

The first verifier correctly recomputed locked metrics but depended on ignored
corpus/runtime caches and did not persist development rankings. The corrected
`verify-results` rebuilds corpus metadata and status from frozen KB source,
validates tracked dev/locked rankings and memberships, recomputes metrics and
paired outcomes, checks all tracked artifact hashes, and works without ignored
model/cache files. `verify-runtime-reproduction` is explicitly separate and
optional for local encoder/embedding/stable-run verification.

The final taxonomy correction additionally recomputes every error row from the
gold mapping, classifier prediction, R0/R1 rankings, evidence contract, and
hard-negative IDs. Category F now requires a non-gold sibling section that ranks
above first strict gold (or is present when gold is absent); the gold chunk
itself cannot trigger F. Category D covers a wrong classifier whenever strict
gold remains in R1 top 3 after the more specific C/E/F/G cases. This correction
does not rerun or alter development selection, locked rankings, metrics, paired
outcomes, safety diagnostics, or multi-document diagnostics.

## Limitations

This is a small synthetic KB and mapping. The classifier achieved 33/60 (0.55)
diagnostic accuracy on these synthetic queries, and its probabilities are not
calibrated. Development improvement did not generalize to locked results. The
experiment supports a bounded R0 decision, not a claim about all intent-aware
retrieval designs.
