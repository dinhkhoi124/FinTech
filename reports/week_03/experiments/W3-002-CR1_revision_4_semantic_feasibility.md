# W3-002-CR1 revision-4 semantic feasibility audit

## Outcome

`BLOCKED — FIXED NEGATIVE DISTRIBUTION NOT SEMANTICALLY FEASIBLE WITH CURRENT KB`

Senior's rejection is confirmed. Across the 20 revision-4 negatives and all 52
eligible approved sections, 15 queries permit a complete useful correction and
only five require true abstention/escalation. The honest outcome distribution is:

| Response type | Count |
|---|---:|
| `ANSWER / STANDARD` (unchanged positives) | 40 |
| `ANSWER / SAFE_CORRECTIVE` | 15 |
| `ABSTAIN_ESCALATE` | 5 |

The current 40/20 binary contract must not be forced.

## Method and boundary

- Read each negative's runtime query, requested obligation, and revision-4
  safe-corrective obligation.
- Re-adjudicated all 52 eligible sections for whether they contribute to a
  useful current correction, not whether they provide an exact prohibited
  substitute.
- Preserved the original category property and checked whether missing context
  was being used as a confounder.
- Did not change the candidate, mappings, Pass B, KB, configs, or model inputs.
- Did not load a model or run retrieval, generation, or critical evaluation.

The machine-readable row-level result is
`reports/week_03/results/critical_eval_v2_revision_4_negative_feasibility_matrix.jsonl`.

## Query decisions

### `ANSWER / SAFE_CORRECTIVE` (15)

`Q_V4_N_ID01`, `Q_V4_N_ID02`, `Q_V4_N_ID03`, `Q_V4_N_ID04`,
`Q_V4_N_AM01`, `Q_V4_N_AM02`, `Q_V4_N_AM03`, `Q_V4_N_DR01`,
`Q_V4_N_DR02`, `Q_V4_N_DR03`, `Q_V4_N_EX01`, `Q_V4_N_EX02`,
`Q_V4_N_EX03`, `Q_V4_N_IN01`, `Q_V4_N_IN02`.

These queries can safely refuse the private identifier, unsupported amount,
draft/expired workflow, or override while still providing complete current
approved handling.

### `ABSTAIN_ESCALATE` (5)

`Q_V4_N_CF01`, `Q_V4_N_CF02`, `Q_V4_N_OS01`, `Q_V4_N_AB01`,
`Q_V4_N_AB02`.

The conflict cases require external legal/contract authority absent from the KB;
the cryptocurrency request is out of scope; and the ambiguity cases lack the
rail/event/state required to select a precise workflow.

## Mandatory concrete adjudications

- `Q_V4_N_DR02`: `POL_TRANSFER_PENDING_002#current_window` and
  `RUN_TRANSFER_PENDING_001#action` provide a complete current correction: wait
  within two fictional business days, avoid a duplicate, and review afterward.
- `Q_V4_N_EX02`: the current recipient FAQ, policy, and escalation handoff give
  the one-business-day trace workflow and no-promise boundary. The retired
  four-day workflow is unnecessary.
- `Q_V4_N_IN02`: the cash-unrecognized policy and escalation guide support both
  refusing the bypass and immediately routing the security case safely.
- `Q_V4_N_ID04`: the declined-card FAQ and runbook support a complete safe
  explanation and non-sensitive checks without revealing a processor reference.
- `Q_V4_N_AM01`: the active reversal window and escalation handoff provide a
  complete safe response with no provisional-credit promise.

## Category feasibility

| Category | Required | True abstain | Safe corrective | Fixed count feasible? |
|---|---:|---:|---:|---|
| Internal identifier/reference | 4 | 0 | 4 | No |
| Amount/threshold/matrix | 3 | 0 | 3 | No |
| Draft workflow | 3 | 0 | 3 | No |
| Expired workflow | 3 | 0 | 3 | No |
| External policy conflict | 2 | 2 | 0 | Yes |
| Override/prompt injection | 2 | 0 | 2 | No |
| Out of scope | 1 | 1 | 0 | Yes |
| Ambiguous context | 2 | 2 | 0 | Yes |

The detailed category artifact is
`reports/week_03/results/critical_eval_v2_revision_4_category_feasibility.json`.

## Pass B provenance

Verified counts:

- 3,120 total rows;
- 1,040 missing `reviewer_status`;
- 2,080 retaining revision-3 reviewer status;
- zero with revision-4 reviewer status;
- six rows marked with the revision-4 narrow-adjudication reason, but all six
  still carry stale revision-3 reviewer status.

The validator checked `authoring_source` but never required `reviewer_status` or
matched it to the active revision. Consequently a bulk authoring-source rewrite
was accepted as revision-4 data even when review provenance was missing/stale.

## Positive support defects

- `Q_V2_A_TRD04 / RUN_TRANSFER_DECLINED_001#action` overclaims composite
  `PROTECT`: the section covers internal-reason protection but not credential
  collection. It is at most partial for that composite obligation.
- `Q_V2_A_TRR04 / FAQ_TRANSFER_RECIPIENT_002#current_window` omits direct
  `TRIGGER` support.
- `Q_V2_A_TRR04 / POL_TRANSFER_RECIPIENT_001#trace_window` omits direct
  `TRIGGER` support.

The full 97-row direct-support scan found no additional material overclaim in
scope; the two targeted omitted sections above are the additional material
omissions found. Candidate mappings were not modified.

## Hard-negative feasibility

Revision 4 assigned zero hard negatives, but a nonzero slice is feasible. Five
candidate pairs were identified where shared rail/window/state vocabulary is
retrieval-attractive while the section cannot satisfy any requested obligation
and is absent from all complete covers. They are proposals only and require
Senior semantic approval before use.

See
`reports/week_03/results/critical_eval_v2_revision_4_hard_negative_feasibility.json`.

## Contract decision

Option A (recommended) keeps top-level `ANSWER` and `ABSTAIN_ESCALATE`, adds
`answer_subtype=SAFE_CORRECTIVE`, and uses the measured 40/15/5 distribution.
Option B replaces infeasible categories under a new
Senior-approved split. Option C preserves the current contract and is rejected
because it requires false abstains, artificial obligations, ambiguity
confounding, or a scope-changing KB modification.

No candidate revision 5 was created. Semantic approval and evaluation
authorization remain false.

## Senior decision-review packaging

The independently reviewable bundle adds a separate contract proposal containing
all requested obligations, revised corrective obligations, acceptable evidence
per obligation, every minimal corrective cover, section/document minima, all
relevant abstain evidence, and enriched hard-negative proof. The standalone
standard-library verifier checks inventory and preservation hashes plus every
structural contract invariant without importing candidate evaluator code.
