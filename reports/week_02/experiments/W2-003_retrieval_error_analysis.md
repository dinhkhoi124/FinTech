# W2-003 Retrieval Error Analysis

The canonical row-level review is
`reports/week_02/results/retrieval_error_analysis.csv`. It contains 28 ANSWER
queries triggered by different top-1, changed first-gold rank, either top-3 miss,
incomplete multi-document coverage, or wrong predicted intent. Ten
ABSTAIN_ESCALATE queries are excluded from A–I retrieval-error categories and
retained separately in `retrieval_safety_diagnostics.csv`.

## Findings

| Reviewed category | Count |
|---|---:|
| A — classifier correct, boost helps | 3 |
| C — classifier wrong, boost hurts | 4 |
| D — classifier wrong, dense retrieval succeeds | 4 |
| E — semantic hard negative outranks gold | 4 |
| F — non-gold sibling outranks gold | 2 |
| G — contract-level multi-document partial retrieval | 3 |
| I — query underspecification / residual semantic miss | 8 |

The automatic taxonomy produced A/C/D/E/F/G/I counts of
3/4/4/4/2/4/7. Manual contract review moved
`Q_LOCK_CARD_DECL_002` from G to I because its two gold sections belong to one
document; it is not one of the four `multi_document` contract rows.

Every row records the decisive query signal, expected gold section(s), actual
higher-ranked non-gold sections, other non-gold top-3 sections, classifier effect,
category-specific rationale, and decision implication. The dominant issue is not
status leakage: both variants retrieve
only the same eligible APPROVED corpus. Section-level distinctions and query
wording often dominate. Three gains from a correct intent signal were outweighed
by four losses and one broken R0 top-1 success.

The explicit four-query multi-document slice has identical R0/R1 mean gold
Recall@3 of 0.666667 and complete coverage of 1/4 (0.25). Per-query missing gold
sections are retained in `retrieval_multi_document_diagnostics.json`.

No substantive KB or gold-mapping defect was found. Frozen W2-002 data was not
changed. The decision implication remains to retain R0; no P1 retriever is opened.

## Review correction incident

**Reproduce:** all ten empty-gold safety probes were labeled `r0_miss_top3` and
`r1_miss_top3`, inflating category I and the review population to 38.

**Root cause:** strict first-gold/miss triggers ran before checking
`expected_response_type == ANSWER`.

**Fix:** strict error slicing now runs only on ANSWER queries; safety rows use a
separate diagnostic schema and make no abstention claim.

**Regression tests:** focused tests reject safety membership in error categories,
require all ten safety diagnostics, and require exactly 28 ANSWER rows.

**Lesson:** empty relevance sets are a different evaluation contract, not a
retrieval miss with reciprocal rank zero.

## Error-taxonomy correction incident

**Reproduce:** six rows were categorized F even though no non-gold sibling from
the gold document displaced strict gold:
`Q_LOCK_CARD_PEND_003`, `Q_LOCK_CARD_REVERT_003`,
`Q_LOCK_CASH_PEND_002`, `Q_LOCK_CASH_PEND_004`,
`Q_LOCK_CASH_UNREC_002`, and `Q_LOCK_TR_DECL_004`.

**Root cause:** the F condition included the gold chunk itself, and D only
covered improved rank rather than retained retrieval success.

**Fix:** one rank-aware, mutually exclusive classifier now applies the frozen
G/A/B/C/E/F/D/I precedence to automatic and reviewed categories. The reviewed
override is limited to the documented `multi_document` contract refinement.

**Regression:** controlled fixtures distinguish gold at rank 1, a non-gold
sibling above/below gold, a hard negative above gold, and a wrong classifier
with strict gold retained. `verify-results` recomputes both categories for every
row and rejects per-row or same-aggregate category tampering.

**Lesson:** aggregate category totals cannot prove row-level taxonomy correctness.

Senior final review accepted the corrected row semantics with verdict
`APPROVE_COMMIT`. This closes W2-003 as DONE / REVIEWED / ACCEPTED and passes the
Week 2 P0 gate without changing the selected R0 retriever or starting Week 3.
