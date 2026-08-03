# W3-002 Retrieval Ablation — R0 vs R1

> Historical numerical diagnostic only. The self-referential mapping audit
> invalidates final model selection; these figures cannot establish a winner.

R0 and R1 used the same frozen Gate v2 policy `S0.40_C0.20`, generator, verifier,
queries, mappings, and context-status filter. R1 alone applied frozen lambda 0.15.

| Metric | R0 gated | R1 gated |
|---|---:|---:|
| Positive grounded recall | 0.625 | 0.575 |
| Safe resolution | 0.750 | 0.717 |
| Wrong-evidence positives | 6 | 6 |
| Negative abstention | 1.000 | 1.000 |
| Unsafe answers | 0 | 0 |
| Complete multi-document | 0/6 | 0/6 |

Paired analysis records 23 both-correct positives, two cases where R1 breaks an
R0 correct answer, nine both-wrong abstentions, and 20 both-correct negative
abstentions. Neither variant is production-eligible because both have six hard
wrong-evidence failures. R1 does not improve safe resolution, so the pre-existing
R0 retrieval choice is retained diagnostically; no new production selection is
authorized. After integrity invalidation, even diagnostic retention must not be
presented as a W3-002 production decision.
