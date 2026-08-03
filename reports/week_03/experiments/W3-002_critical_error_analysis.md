# W3-002 Critical Error Analysis

> This analysis describes what the original evaluator reported. Post-hoc
> integrity review invalidated its mapping semantics, so rows cannot be treated as
> established model failures.

The machine-readable review contains 34 rows covering every V0 non-resolution,
V0/V1 or V0/V2 difference, and incomplete multi-document case. Six are severe V0
wrong-evidence answers: `Q_CRIT_A_003`, `Q_CRIT_A_004`, `Q_CRIT_A_020`,
`Q_CRIT_A_032`, `Q_CRIT_A_036`, and `Q_CRIT_A_040`.

The dominant severe causes are incomplete strict multi-document coverage and
verified extraction from approved but frozen-unmapped evidence. This is not a
citation-integrity failure: exact quotes and metadata verify, but relevance or
required evidence completeness does not. The finding therefore blocks Week 3
despite zero unsupported claims and zero unsafe negative answers.

Regression coverage asserts that wrong-evidence positives classify as
`WRONG_ANSWER`, strict multi-document success requires every gold ID, outcome
partitions total 60, and pre-evaluation mapping/hash drift fails closed. No query,
mapping, threshold, lexicon, or runtime output was changed after evaluation.
