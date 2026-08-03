# W3-002 Gate Ablation — Evidence-gated vs Always-answer

> Historical numerical diagnostic only. Critical-set integrity is invalid and
> the model/pipeline verdict is not established.

Both variants use R0, the same approved/effective-only top-3 context, extractive
generator, strict citation verifier, and fail-closed override/generation rules.
Always-answer bypasses only evidence sufficiency checks.

| Delta (always-answer minus gated) | Result |
|---|---:|
| Answer rate | +0.450 |
| Additional positive answers | +9 |
| Positive grounded recall | +0.175 |
| Negative abstention accuracy | -0.900 |
| Unsafe answers | +18 |
| Unsupported claims | 0 |
| Safe resolution | -0.183 |

The evidence gate prevented unsafe answers through specificity, ambiguity,
retrieval/support, dimension, and override reason codes. Always-answer is a
diagnostic ablation only and cannot be selected for production.
