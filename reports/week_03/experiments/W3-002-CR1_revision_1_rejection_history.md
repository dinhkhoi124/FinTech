# W3-002-CR1 — Candidate Revision 1 Rejection History

## Senior verdict

```text
FIX_REQUIRED
```

Candidate revision 1 is invalidated. Its manifest is preserved byte-identically at
`reports/week_03/results/critical_eval_v2_revision_1_rejected_manifest.json` with
SHA-256:

```text
39af29f929ef9a9287808c26d62787079e376a8b7ac05847fa10729d27374b99
```

## Root cause

Revision 1 embedded substantive support assignments in Python scenario
specifications through `_direct`, `_partial`, `_contradiction`, and `_forbidden`.
The support-plan writer copied those assignments, and Pass B then expanded them
with intent/family heuristics. The resulting chain was:

```text
preselected evidence roles
→ generated judgments
→ derived mapping
```

It was not an independent section-content audit and could not discover supporting
sections omitted from the embedded answer key. Metadata claiming independence did
not repair that construction.

## Rejected diagnostic results

- Candidate bytes frozen: true
- Structural integrity verified: false after Senior review
- Pre-evaluation integrity passed: false after Senior review
- Package status: `CANDIDATE_INVALIDATED / REAUTHORING_REQUIRED`
- DIRECT_SUPPORT: 81
- PARTIAL_SUPPORT: 20
- Derived hard-negative assignments: 20
- Section minima: 31 single-section / 9 two-section positives
- Document minima: 34 single-document / 6 multi-document positives
- Structurally reported false abstains: 0

These values are history only and must not be used as revision-2 targets.

## Superseded artifacts

Revision 2 supersedes the revision-1 Pass B support plan, generated judgments,
Pass C mapping, negative audit, forbidden audit, dataset manifest, candidate
manifest, verification output, test evidence, and external review bundle. Pass A
scenario/query/obligation text may be retained only after proving it contains no
hidden evidence roles.

## Continuing boundary

```text
senior_semantic_review_approved=false
evaluation_authorized=false
critical_evaluated=false
model_verdict=NOT_ESTABLISHED
Week 3 P0=BLOCKED / IN PROGRESS
Week 4=BLOCKED / NOT STARTED
```
