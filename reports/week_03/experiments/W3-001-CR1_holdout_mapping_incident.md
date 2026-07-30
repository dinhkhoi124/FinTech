# W3-001-CR1 Holdout Mapping Incident

## Reproduce

An exhaustive review of all ten positive holdout queries against all 52 eligible
approved KB sections found three direct sections absent from acceptable mappings.
The omission rate was 3/10 positive queries.

## Root cause

Evidence mapping was performed section-selectively rather than through a final
exhaustive all-eligible-section support audit.

## Impact

One omission produced a false wrong-evidence failure in the original evaluation.
The other two did not affect current metrics because their sections were not cited,
but they demonstrate that the locked relevance labels were incomplete.

## Correction

The original holdout dataset and original FAILED result remain immutable. A
Senior-approved three-row adjudication overlay adds only acceptable evidence and
is applied only when recomputing relevance metrics from frozen outputs.

## Integrity safeguards

- Exactly ten unique positive audit rows and exactly three approved omissions.
- Exactly three overlay rows, each tied to an audited omission.
- No gold removal/replacement or query metadata change.
- Added evidence must be approved, effective, and quote-exact at the evaluation date.
- Original holdout and output hashes must match before adjudication verification.
- Original and adjudicated metrics remain separate.

## Regression tests

Tests cover exhaustive audit cardinality, exact omission cardinality, direct
support for each accepted section, overlay scope and row count, gold/metadata
immutability, non-audited and ineligible evidence rejection, quote matching,
separate original/adjudicated metrics, and proof that tracked verification does
not invoke encoder inference, retrieval, or generation.

## Lesson

Every future locked or critical positive mapping must receive an exhaustive
direct-support audit before model evaluation. For W3-002, every positive query
must be checked against all 52 eligible approved sections, the complete support
set and audit hash must be frozen, and no evaluation may begin while an omission
is unresolved.

## Limitation

The holdout remains a post-hoc adjudicated evaluation rather than a pristine
untouched-label evaluation. The adjudication is accepted because all ten positives
were exhaustively reviewed against all 52 eligible sections, corrections were
applied symmetrically, and the original outputs remain immutable.

## Final disposition

Senior verdict is `APPROVE_COMMIT — QUALIFIED POST-HOC PASS`. The original FAILED
result is preserved as historical evidence; the post-hoc adjudicated result is
PASS / REVIEWED / ACCEPTED. Evidence Gate v2 is selected for future W3-002
evaluation, but W3-002 remains QUEUED / NOT STARTED and Week 3 P0 remains IN
PROGRESS.

Before W3-002 critical evaluation:

1. Author and freeze the critical set.
2. Audit every positive query against all 52 eligible approved sections.
3. Freeze a complete direct-support evidence set.
4. Record a pre-evaluation mapping-audit SHA-256.
5. Do not execute critical evaluation while any mapping omission remains.
