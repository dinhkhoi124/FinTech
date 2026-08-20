# W3-003-RM2-RED1 consumed-holdout access incident

## Incident summary

The previous verification session called the legacy
`run_nonlocked_regression()` helper while verifying the already-created RED1
candidate. The helper implicitly loaded both an original W3-001 development
membership and the consumed W3-001-CR1 membership. This was a verification
boundary breach. The contaminated W3-001 result is invalid and is not used in
RED1-RCV1 certification.

- Classification: `VERIFICATION_BOUNDARY_BREACH / CONSUMED_HOLDOUT_READ`
- Prohibited membership identifier:
  `w3_001_cr1_observed_holdout_now_development`
- Triggering helper:
  `src/payresolve_ai/generation/pipeline_v3.py::run_nonlocked_regression`
- Access type: automatic file read into the helper's in-process membership
  collection
- Individual consumed rows printed: no evidence found; none are reproduced in
  this report or the recovery evidence
- Contaminated result returned/used: the helper result is treated as
  contaminated and invalid regardless of whether individual rows were rendered
- EV1 accessed by the previous session: false, per the incident record
- Consumed holdout accessed by the previous session: true

No authoritative incident timestamp was persisted. File metadata and the task
handoff were therefore used only as bounded audit evidence; they cannot prove a
complete prior-session command chronology.

## Impact classification

The breach invalidates the previous W3-001 verification result. It does not by
itself prove EV1 contamination or production-candidate contamination.

- Evidence invalidated: previous-session W3-001 result produced through the
  legacy multi-membership helper
- PRE_INCIDENT diagnostic evidence: retained as diagnostic history only; not
  sufficient for RCV1 certification
- Initial candidate status:
  `QUARANTINED_PENDING_CLEAN_REVERIFICATION`
- Final RCV1 candidate status after clean verification:
  `CLEAN_REVERIFICATION_CANDIDATE / AWAITING SENIOR REVIEW`

## Post-access production-edit audit

The current session captured SHA-256 and byte identities before any edit:

| Production file | Bytes | SHA-256 |
|---|---:|---|
| `routing_v3.py` | 29,572 | `a3ca581dfcd963fa8e36179c65bc1854a6b1748e86486de6a73a98dcb38093a9` |
| `pipeline_v3.py` | 24,717 | `4d5b96679fd610f7ddadc245486aec0750fc02f3045c453409f49b645940f203` |
| `support_v2.py` | 13,006 | `1f354bb160d3c75891dc2c004734fdfdf2e6650475c172ffb7e029f6cb8f09c9` |
| `targeted_extractive.py` | 3,518 | `e7a1a8af4b2b89d6652348ea3267d2ace99ad7d64583dfaf4d77553ce8fa27ea` |

Observed last-write timestamps predate the current recovery session. Two files
were written after the focused test file was created, which is consistent with
normal RED1 test-first implementation but is not sufficient to order those
writes relative to the later incident. No authoritative incident timestamp,
post-incident diff, or other credible evidence of a production edit after the
forbidden access was found.

Required classification fields:

- `post_incident_production_edit_evidence_found=false`
- `candidate_source_contamination_status=QUARANTINED_PENDING_CLEAN_REVERIFICATION`

The first field means “no credible evidence found by the available mechanical
audit”; it is not an assertion that unavailable history was exhaustively proven.
All four production SHA-256 values remained identical throughout RCV1.

## Root cause

The legacy helper has no membership argument or allowlist. It constructs a
two-entry `memberships` dictionary unconditionally:

1. `w3_001_observed_development`, resolved through a broader W2 mapping; and
2. `w3_001_cr1_observed_holdout_now_development`, loaded from the v2 holdout
   config and historical holdout outputs.

It then iterates every dictionary entry. Consequently, calling the helper for a
development-only check necessarily opens more evidence than the RED1 contract
authorizes. The original development resolver also reads a W2 mapping that
contains locked rows before filtering development rows, so it is unsuitable for
the RCV1 clean boundary as well.

## Containment and helper correction

RCV1 did not modify the frozen production helper. Instead it introduced the
verification-only module
`src/payresolve_ai/generation/red1_verification.py` and made it the sole W3-001
clean-verification path.

The new path:

- requires membership ID
  `EXPLICIT_NON_LOCKED_W3_001_DEVELOPMENT_ONLY`;
- requires exact path `data/evaluation/evidence_gate_dev_v1.jsonl`;
- rejects any other identifier/path before the opener is called;
- binds every opened artifact by exact relative path and SHA-256;
- uses the already-resolved W3-001 development output instead of reopening the
  broader W2 mapping;
- records the nine opened paths and reports forbidden file opens as zero;
- never calls `run_nonlocked_regression()`.

The legacy helper remains in the frozen production file and is explicitly
deselected from RED1-RCV1. This residual legacy API is not an authorized RED1
certification path and should be removed or redesigned only under a separate
production-change task.

## Regression prevention

`tests/test_red1_verification_boundary.py` proves:

- exact W3-001 development membership accepted;
- consumed W3-001-CR1 identifier/path rejected before open;
- EV1 identifier/path rejected before open;
- unknown evaluation membership rejected before open;
- exact ID paired with a non-allowlisted path rejected before open.

Result: 5/5 PASS and `forbidden_file_open_calls=0` for every negative case.

## Clean recovery result

- Boundary regression: 5/5 PASS.
- Focused RED1 suite: 20/20 PASS.
- Root A: 4/4; Root B: 4/4; R1-R6: 6/6; fallback: 2/2;
  NEXT_ACTION/RETRY: 2/2.
- Existing safe V3 allowlist: 23/23 PASS; legacy consumed helper test deselected.
- W3-003 development: 14/14 PASS, distribution 2 STANDARD / 7 CORRECTIVE /
  5 ABSTAIN, zero citation failures, zero ineligible selections, deterministic.
- W3-001 exact development: 7/10 safe STANDARD, 3 abstentions, 10/10
  safety probes safe, zero unsafe STANDARD safety answers, deterministic.
- Current-session consumed/EV1/locked evidence opens: zero.
- Production bytes changed during recovery: false.

## Lesson

An artifact being historically renamed “development” does not make it eligible
for a new verification boundary. Verification helpers must accept an explicit
membership identity, bind exact paths and hashes, and reject unknown or consumed
evidence before any file open. Recursive discovery, multi-membership defaults,
and filter-after-read designs are unsafe for evaluation recovery.

## RCV2 repository-level closure

Senior found that RCV1 retained an executable legacy helper despite providing a
safe explicit alternative. RCV2 replaces `run_nonlocked_regression()` with the
deterministic `PipelineV3Error`
`LEGACY_NONLOCKED_REGRESSION_DISABLED_USE_EXPLICIT_RED1_VERIFICATION` before any
filesystem/evaluation operation. Its direct mandatory regression patches both
`Path.read_text` and `load_jsonl`, observes zero calls, and passes. The explicit
hash-bound `red1_verification.py` route remains unchanged; semantic RED1 output
hashes and safety results equal RCV1. No second contamination occurred.

## RPF1 reporting reconciliation

RCV1 is retained as historical incident/recovery context only. The current
candidate is RCV2, whose `pipeline_v3.py` identity is 18,543 bytes and
`832efe715586fd50f24c6c1a2bfb5969dc60f9fb870998d3b3c01be0df270058`; the
historical RCV1 pipeline identity was 24,717 bytes and
`4d5b96679fd610f7ddadc245486aec0750fc02f3045c453409f49b645940f203`.

RPF1 reran the legacy safety regression (1/1), boundary suite (5/5), focused
remediation suite (20/20), and safe V3 allowlist (24/24, including legacy).
The two permitted clean replays retained their recorded W3-003/W3-001 hashes
and zero forbidden opens. The command/exit-code record is
`reports/week_03/results/w3_003_rm2_red1_rcv2_command_evidence.json`.

This is evidence/package reconciliation only: it does not alter the incident
classification, invalidate additional evidence, authorize a new evaluation, or
close the W3 P0 gate. RPF1 awaits independent Senior review.
