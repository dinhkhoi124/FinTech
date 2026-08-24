# Project State

> This file is the concise handoff that every new Codex chat/session must read and update.

## Current status
- Project: PayResolve AI
- Current phase: Phase 3 — Grounded RAG + safety
- Current week: Week 3
- P0 gate status: BLOCKED / REMEDIATION REQUIRED
- Active task: `W3-003-EV2-A4-ATT1-PUB1` — PUBLISHED ATTESTATION EVIDENCE / AWAITING SENIOR REMOTE VERIFICATION
- Next task: Senior fresh-remote verify ATT1, then issue real A4 authorization if approved; E1/EV2 remain unauthorized and unexecuted.
- Last updated: 2026-08-25 by Codex

The current authoritative status is RM2: `CLOSED / COMMITTED / PUSHED / REMOTE
VERIFIED`. Its implementation publication commit is
`cd97de602140e334ec499e8dfa27fa08ec1a6260`. RCV2 is `IMPLEMENTED / CLEAN
VERIFIED / SENIOR APPROVED / PUBLISHED`; RPF1 is `SENIOR APPROVED /
REPORTING-EVIDENCE RECONCILED / PUBLISHED`; PUB1 is `SENIOR BYTE REVIEWED`;
PUB2-WF1 is `SENIOR APPROVED`; and PUB2 is `COMMITTED / PUSHED / REMOTE
VERIFIED`. RCV1 is a historical predecessor only. EV1 completion, remotely
verified N1 NB1 reporting closure, and Senior-accepted RM1 RCA remain frozen
history. Earlier readiness, authorization, and execution sections are dated
historical milestones and do not override the current recovery state.

## W3-003-EV2-A4-ATT1 pre-E1 runtime environment and local model snapshot attestation — 2026-08-25

The A3 FIX4 package remained identity-locked at manifest SHA-256
`19ad35b27bd3f60e0a76ae7e42ea4c06a197166e1e9ae3ea26dbecc05ae5ee54`.
The intended E1 runtime is CPython 3.11.9 64-bit CPU at
`.venv-semantic\\Scripts\\python.exe`: all 30 frozen pins match
`requirements/week1-semantic.txt`, and `pip check` passed. Offline controls
were fixed, the local MiniLM snapshot at revision `1110a...4d41` passed all
11 file/hash/size checks (91,578,415 bytes), and frozen corpus/runtime assets,
candidate source tree, and final R0 decision all passed.

The read-only load used `local_files_only=true`, made zero network attempts,
loaded the 52x384 runtime without ranking or encoding any EV2 query, and
produced environment fingerprint
`f49e29f3ad3338a191f50e42e28fd2335a36f670541c9eb7337f0bcdcb478a7d`.
The deliberately non-authorizing preauth payload SHA-256 is
`f7b59287f478f6fbe6878604a0d2d0ada6f943d3201aaf8cc3eabf1de4488cf3` and
the E1 validator rejected it before any runner/retrieval/EV2 call with
`A4_BINDING_MISMATCH:authorization`. No real A4 receipt, consumption receipt,
raw output, E1 row, EV2 query, staging, commit, or push exists. Status:
`A4_ATT1_PUBLISHED_AWAITING_SENIOR_REMOTE_VERIFICATION`.

Future real E1 remains conditional on a separately Senior-authorized just-before-
execution re-attestation: verify the frozen requirements and provenance SHA/blob,
set the exact offline/thread/hash controls, use CPython 3.11.9, rerun ATT1, and
require the same environment fingerprint and all ATT1 identities before creating
and using a real A4 receipt. No install, edit, or mutation may intervene.

## W3-003-EV2-A3-FIX4 frozen R0 retriever execution binding — 2026-08-25

Published FIX3 is preserved byte-for-byte at SHA-256
`5e1af86ecf60accddfe6b201cb7c62e4f29b4dde3c1ac3573ed989f832a2f0d1`.
It was technically published and remote-verified at `aaaa9f...effc7`, but the
post-publication A4 cross-check found that E1 incorrectly derived runtime mode
from development `selected_lambda=0.15` rather than the authoritative Week-2
final decision. FIX3 is therefore `PUBLISHED_REMOTE_VERIFIED_BUT_SUPERSEDED_BEFORE_A4`
for `E1_RETRIEVER_SELECTION_DEFECT`; EV2 was not executed or consumed.

FIX4 binds `reports/week_02/results/retrieval_version_manifest.json` at working
SHA-256 `c8834784...9c3ce` and candidate blob `807b5413...7ea4d`. Its finalized
Senior-approved selected retriever is R0. Before any receipt, E1 now validates
that decision and fails closed with `FROZEN_RETRIEVER_DECISION_MISMATCH_BEFORE_CONSUMPTION`;
the R0 ranking branch passes `boost=None`, never development lambda 0.15. A4,
consumption, raw-manifest, and R1 scorer bindings all carry the same R0 and
decision hash. Synthetic-only tests cover R1/missing/unknown/drift/finalization
failures and capture `boost=None`; no real retriever or EV2 query ran.

Two deterministic builds have mismatch count zero, retain 30 prior mutations,
all nine safety-negation checks, 24/18/12/6 strata and denominator 42. The
combined regression suite passes 64/64. Active manifest SHA-256 is
`19ad35b27bd3f60e0a76ae7e42ea4c06a197166e1e9ae3ea26dbecc05ae5ee54`.
Status is `A3_FIX4_FROZEN_PACKAGE_READY_FOR_SENIOR_REVIEW`; A4 remains
unauthorized, E1/EV2 row 1/execution/consumption false, and no production, Gold,
KB, stage, commit, or push changed.

## W3-003-EV2-A3-FIX3 final pre-A4 safety and causal closure — 2026-08-24

FIX2 is byte-preserved at SHA-256
`c892ed2f551860bd40899a4aa6e4ef33d29226d342c522817c5b583dc3d2115b`
and recorded as `REJECTED_BY_SENIOR — PRE_A4_SAFETY_AND_CAUSAL_INTEGRITY_DEFECT`.
FIX3 adds only bounded scorer/package repairs: production raw-schema invariants,
rule-local safety negation, actual approved/effective/unexpired eligibility,
and the frozen causal failure precedence. Synthetic R1 runs pass 60/60 at
24/18/12/6 with denominator 42; all 30 mutations pass, including eight raw
schema fail-closed cases, nine safety-negation regressions, causal precedence,
and expired-approved-evidence parity. The deterministic two-build mismatch is
zero. No E1 harness or candidate/EV2 inference ran; A4 remains unauthorized,
and evaluation execution/consumption remain false.

Status is `A3_FIX3_FROZEN_PACKAGE_READY_FOR_SENIOR_REVIEW`. No Pass A/B/C,
classification, production, KB/runtime, or EV2 query bytes changed. No stage,
commit, or push occurred.

## W3-003-EV2-A3-FIX2 final pre-EV2 scorer closure — 2026-08-24

Senior rejected FIX1 for an R1 scorer/root and product-gate integrity defect.
Rev1 remains preserved at `01e610...96e72`; FIX1 is now preserved byte-for-byte
at `1e45c8...051f7` with status `REJECTED_BY_SENIOR —
R1_SCORER_AND_PRODUCT_GATE_INTEGRITY_DEFECT`. A2 remains closed and its five
frozen identities remain unchanged.

FIX2 requires explicit scorer `--root .`, loads authoritative
`semantic_stratum` only from frozen Pass A, and proves the real distribution
24 STANDARD / 18 SAFE_CORRECTIVE / 12 HARD / 6 AMBIGUOUS. Wrong abstention is
derived only from STANDARD+SAFE_CORRECTIVE, denominator 42; the two ambiguous
SAFE cases are excluded. Route-correct factual output without a complete
selected support set is a utility failure and not a product success.

The scorer now reuses production `verify_draft` semantics, freezes global
reason-family compatibility, covers all 27 unique forbidden-action codes with
a fail-closed registry, and emits the full causal trace plus ordered failure
taxonomy. E1 binds a canonical hash of every tracked `src/payresolve_ai/**`
path/byte from candidate `8492659...`, verifies the complete working source
tree before row 1, and emits a strict 60-row raw manifest with physical row,
order, A3/A4, candidate/tree, runtime, input, case-order, consumption, and E1
bindings. R1 rehashes raw data before Gold, then rehashes every frozen Gold,
runtime, evaluator, registry, and package input.

The actual future R1 CLI ran against real frozen Pass A/B/C plus synthetic raw
traces only: exit 0, final PASS, 24/24, 18/18, 12/12, 6/6, denominator 42,
citation correctness 1.0, evaluator integrity PASS, reproducibility PASS.
Seventeen focused FIX2 mutations pass, including D06/D17 incomplete support,
fabricated exact-quote failure, unknown reason, raw reorder/tamper, Gold,
evaluator/mapping and source-tree drift, plus credential, PIN, OTP, unsupported
account assertion, guarantee, security-bypass, and audit-record deletion.
Deterministic mismatch is zero; focused tests pass 17/17 and combined
production/A1/A2/A3 regression passes 59/59. Active manifest SHA-256 is
`c892ed2f551860bd40899a4aa6e4ef33d29226d342c522817c5b583dc3d2115b`.

Status is `A3_FIX2_FROZEN_PACKAGE_AWAITING_SENIOR_REVIEW`. No Pass A/B/C,
classification, production, or EV2 query bytes changed. A4 remains
unauthorized; real EV2 inference, row 1, execution, and consumption remain
false. No stage, commit, or push occurred.

## W3-003-EV2-A3-FIX1 evaluator/E1 integrity correction — 2026-08-24

A3 Rev1 is preserved at SHA-256 `01e610...96e72`. Its identity and
fingerprint-only evidence passed, but Senior rejected the evaluator/E1
execution-integrity claims; Rev1 never authorized evaluation.

FIX1 binds the actual production raw schema and source-backed reason grammar,
persists separate 60-row EV1 and Critical Rev7 hash-only registries, and
recomputes zero exact/normalized collisions without claiming semantic
paraphrase disjointness. The subprocess success/error sentinel probe passes.
All 17 synthetic evaluator cases pass, including explicit utility versus
zero-tolerance separation; the replicated aggregate is 24/24 STANDARD, 18/18
SAFE_CORRECTIVE, 12/12 HARD, and 6/6 AMBIGUOUS with answerable denominator 42.
A development-only `run_case_v3()` invocation passes directly through the pure
adapter.

The 60-row sanitized E1 input exposes only ordinal, case ID, query, and query
hash. The guarded executable path verifies A4 plus all bound identities, writes
the atomic row-1 consumption receipt before production import/call, persists
raw rows before scoring, disables resume, and ends before gold/evaluator load.
Dummy execution proves pre-row failure remains unconsumed and post-row-1
failure remains consumed. Deterministic regeneration mismatch count is zero;
the focused suite passes 22/22 and combined production/A1/A2/A3 regression
passes 64/64.

Status is `A3_FIX1_FROZEN_PACKAGE_AWAITING_SENIOR_REVIEW`. A2 remains `CLOSED /
COMMITTED / PUSHED / REMOTE VERIFIED`; A4 is unauthorized; EV2 is `NOT EXECUTED
/ NOT CONSUMED`; no stage, commit, or push occurred.

## W3-003-EV2-A2-PB1-FIX2B final reconciliation — 2026-08-24

Fresh preflight matched `main` and local/origin/fresh remote
`8492659a50fe00f066f9f64d8759d544356b3a41`, with zero staged, production, or
KB diffs. Pass A v3 and every frozen FIX2/FIX2A semantic input matched its
locked identity. Exact FIX1 Pass B/C were preserved under `_pre_fix2b` at
`5b0a55...4d209` and `7197be...1117d`.

Senior explicitly adjudicated all 17 FIX2A third projections without another
reviewer. Across the 65 non-HARD pairs, the final decision sources are exactly
40 current, 24 blind1, one unique tiebreak, and zero unresolved. FIX2B applied
only those frozen decisions plus H01/H02's authorized state-compatibility
changes. The exact active Pass-B diff contains 27 rows: two Senior HARD, 24
blind1, and one unique tiebreak.

Final Pass B remains 3,120 unique pairs and 52/case, with 68 complete, 59
partial, 199 contextual, 188 contradiction, and 2,606 irrelevant rows. Its
SHA-256 is `f70af099f9842c6d51ad8e75219b5eb8a074a88fe7a3dc4914306fe32defb1d2`.
Proof regeneration passes 24/24 STANDARD, 18/18 SAFE_CORRECTIVE, 12/12 HARD,
and 6/6 ambiguous. A01 retains no positive support. Pass C was derived twice
with byte-identical output: 60 rows, routes 24 STANDARD / 20 SAFE_CORRECTIVE /
16 ABSTAIN_ESCALATE, SHA-256
`04c99c88926b306fa44d6169fdf22507d418311e22d491384344585bbc336431`.

Status is `A2_PB1_FIX2B_READY_FOR_SENIOR_REVIEW`. The A2/FIX2B regression suite
passes 137/137. No new semantic authoring round, reviewer, candidate inference,
EV2 execution/consumption, A3, notebook, stage, commit, or push occurred.

## W3-003-EV2-A2-PB1-FIX2A normalized projection and tiebreak stop — 2026-08-21

Fresh preflight remained pinned to `main` and local/origin/fresh remote
`8492659a50fe00f066f9f64d8759d544356b3a41`, with zero staged, production, or
KB diffs. Pass A v3, FIX1 active Pass B/C, original FIX2 packet/decisions/
comparison/ledger, and KB matched their locked hashes and remain immutable.

`SEMANTIC_DECISION_PROJECTION_V2` recomputed 76 disagreements: 11 imported
HARD and 65 non-HARD. `GOLD_IMPACT_PROJECTION_V1` recomputed 58: 2 imported
HARD and 56 non-HARD. Senior adjudicated all 33 original exact-field HARD
differences, authorizing only H01 action and H02 handoff `state_match` changes;
the other 31 imported judgments remain the planned source of record.

The exact 65 non-HARD V2 disagreement pairs were sanitized and frozen at
SHA-256 `f2ecb40ab1691fb940a8a341fc47bd24ffc72c443b332358c70aed8210ee03e6`.
A distinct second fresh-context subagent received only this packet/hash, global
semantic rules, and schema. It returned 65 validated decisions at SHA-256
`379ca46bc56d50af04058e9809fabbf18dc97b1f75aadf088344ede94a9765ba`:
9 complete, 8 partial, 38 contextual, 1 contradiction, and 9 irrelevant.

Three-way comparison resolved 26 pairs to current and 22 to the blind1/tiebreak
projection, but 17 tiebreak projections matched neither side. Status is
`A2_PB1_FIX2A_UNRESOLVED_THREE_WAY_SEMANTIC_CONFLICT`. Per stop rule, the
reviewer was not relaunched; H01/H02 were not yet applied; no final correction
ledger, Pass B, proofs, or Pass C was created. Active Pass B/C remain FIX1 bytes
`5b0a55...4d209` / `7197be...1117d`. The A2 suite passes 121/121. A3,
candidate inference, EV2, stage, commit, and push remain unexecuted/unauthorized.

## W3-003-EV2-A2-PB1-FIX2 blinded semantic adjudication stop — 2026-08-21

Fresh preflight matched `main`, local HEAD, origin/main, and fresh remote at
`8492659a50fe00f066f9f64d8759d544356b3a41`, with zero staged, production, or
KB diffs. Pass A v3 and the active FIX1 Pass B/C matched their locked hashes.
The FIX1 Pass B/C were preserved byte-for-byte under `_pb1_fix1_pre_fix2` at
`5b0a55...4d209` and `7197be...1117d`.

The parent built and froze a sanitized 514-row packet at SHA-256
`01ceaa093f69887a4a9eb47ebaf3d5e49b87d3cfd17a45a5c8f06f67a216420c`.
One fresh-context isolated subagent received only that packet/hash, the locked
class definitions, and the output schema. It authored 514 decisions at SHA-256
`4292c2d4f0dd3db420ccec6fdb77f02e17edc82de01e1e33e3e44aa0a9a49092`:
66 complete, 60 partial, 197 contextual, 185 contradiction, and 6 irrelevant.
The parent authored no decisions, and validation/freeze completed before current
Pass B was opened.

Comparison found 230 semantic exact matches and 284 differences. Thirteen of
the 23 FIX1 corrections were independently confirmed and ten disagreed; 274
differences were outside that prior correction set. Thirty-three comparison
differences touch imported HARD judgments across H01, H02, H05-R1, H06-R1,
H09-R1, H10, H11, and H12. Per the mandatory stop rule, status is
`A2_PB1_FIX2_IMPORTED_HARD_SEMANTIC_CONFLICT`. Active Pass B/C remain unchanged
at `5b0a55...4d209` and `7197be...1117d`; no final gold was derived. The A2
regression suite passes 110/110. A3, candidate inference, EV2, staging, commit,
and push remain unexecuted/unauthorized.

## W3-003-EV2-A2-PB1-FIX1 semantic correction — 2026-08-21

Senior found that `EV2-A2-S19 × RUN_TRANSFER_PENDING_001#checks` used a
pending-state/masked-reference check as proof of a routing obligation. FIX1
preserved the exact pre-correction Pass B and Pass C at SHA-256
`7dd4c196...c50b6` and `e5f28b1...0f99`, then independently reviewed exactly
the 514 current non-IRRELEVANT rows: 70 complete, 51 partial, 196 contextual,
and 197 contradiction rows. Sixty imported HARD rows were included and passed
with zero semantic conflict or mutation.

The audit retained 491 decisions and corrected 23. S19 `#checks` is now
contextual and its two false composite support sets are gone; only
`RUN_TRANSFER_PENDING_001#action` completes S19. C09's policy/runbook review
clauses now cover masked review only, so both minimal sets require
`FAQ_TRANSFER_DECLINED_001#safe_message`. The same safe-message distinction was
applied to S14. Additional corrections separate conditional triggers from
handoff actions, recover hidden support in mixed ATM-recognition clauses, and
remove eleven non-explicit contradictions.

Corrected Pass B remains 3,120/3,120 unique pairs and 52 per case, with counts
66 complete, 57 partial, 205 contextual, 186 contradiction, and 2,606
irrelevant; SHA-256 is
`5b0a55b0d7b9e1d0aede02b4858441390d5b1945dbd0dd5689f0098304f4d209`.
Mechanical proof derivation remains feasible at 24/24 STANDARD, 18/18
SAFE_CORRECTIVE, 12/12 HARD, and 6/6 ambiguous. Corrected Pass C has 60 rows,
route counts 24 STANDARD / 20 SAFE_CORRECTIVE / 16 ABSTAIN_ESCALATE, and
SHA-256 `7197be43ad32e88a13c3567c52f30ec7ac3e8bcdb1c1c576fbefed661ea1117d`.

Status is `PB1_FIX1_SEMANTIC_AUDIT_PASS_AWAITING_SENIOR_REVIEW_AND_A3` and
external handoff status is `A2_PB1_FIX1_READY_FOR_SENIOR_REVIEW`. Pass A v3 is
unchanged at `f66ce6...66541`; obligation classification, production, and KB are
unchanged. Candidate inference, EV2 execution/consumption, A3, stage, commit,
and push remain false. Notebook requirement is false for this gold-integrity
correction; the future frozen EV2-R1 result stage still requires the notebook.

## W3-003-EV2-A2-PB1 final independent Pass B — 2026-08-21

Senior approved Pass A v3 and authorized the full independent Pass B. Preflight
matched branch `main`, local HEAD, origin/main, and fresh remote at
`8492659a50fe00f066f9f64d8759d544356b3a41`; staged and production/KB diffs
were zero. Pass A v3 remains byte-frozen at SHA-256
`f66ce6b0fa6c86a0cf7e3cc4aba33f3d76699e7981630a8b9b748ce979d66541`.

All 104 Pass-A obligation usages are classified without candidate data: 7
`KB_FACTUAL_PREREQUISITE`, 60 `KB_FACTUAL_RESPONSE_OBJECTIVE`, 12
`REQUESTED_FACTUAL_RESOLUTION`, 19 `CONTROL_PLANE_BOUNDARY`, and 6
`SAFE_STOP_CONTROL`. Final Pass B contains exactly 3,120 unique case/evidence
pairs, 52 per case. It includes 2,496 new content-grounded judgments and 624
mechanical imports from FIX1B/FIX2/FIX3 with zero semantic mutation. Support
classes are 70 complete, 51 partial, 196 contextual-insufficient, 197
contradiction, and 2,606 irrelevant. Active Pass B SHA-256 is
`7dd4c196a8c45cb31ef0d549db3d6e048de78a8fb12f10cedb8f714c6cdc50b6`.

Mechanical proof derivation passes 24/24 STANDARD, 18/18 SAFE_CORRECTIVE,
12/12 HARD, and 6/6 ambiguous cases. A01/A02/A04/A05 derive
`ABSTAIN_ESCALATE`; A03/A06 derive `SAFE_CORRECTIVE` from grounded ATM safety
gates. Pass C therefore contains 60 rows with 24 STANDARD, 20 SAFE_CORRECTIVE,
and 16 ABSTAIN_ESCALATE routes; SHA-256 is
`e5f28b1e8cb44760363b83e42fe4d36dad132548a2f39810cb671b201cb90f99`.
The PB1 fail-closed validator and retained integrity/mutation suite pass 87/87.

Status is `A2_PB1_READY_FOR_SENIOR_REVIEW`. Pass A v3 is Senior-approved and
byte-frozen; Pass B is independently reviewed; Pass C is mechanically derived.
A2 is not frozen and A3 is not started. Evaluation remains unauthorized; EV2
is `NOT EXECUTED / NOT CONSUMED`; W3 P0 and W4 remain blocked. Candidate
inference and consumed EV1/Rev7 case-level access did not occur. No notebook is
created for PB1; the future frozen EV2-R1 product-result report must create the
mentor-facing reproducible notebook. No stage, commit, or push occurred.

## W3-003-EV2-A2-FIX3 Pass A v3 replacement feasibility — 2026-08-21

Senior accepted FIX2A's five-case conflict set and authorized exactly five
replacements. Pass A v2 is byte-preserved at
`data/evaluation/w3_003_ev2_pass_a_v2_pre_fix3.jsonl`, SHA-256
`71a353f79f3a5bbdbf8faf61b63b08f842046f1082d32c3e995feaf928d146d3`;
Rev1 remains `9ef421...b567`. Active Pass A v3 retires H03/H04/H07/H08-R1/H09,
adds H03-R1/H04-R1/H07-R1/H08-R2/H09-R1, and is frozen at SHA-256
`f66ce6b0fa6c86a0cf7e3cc4aba33f3d76699e7981630a8b9b748ce979d66541`.
All 55 other rows are canonical and raw-line byte-equal.

Pass A v3 has 60 unique IDs/families and the required 24/18/12/6 distribution.
HARD family counts are 3 no-approved, 2 prohibited, 2 account-specific, and 5
genuine-conflict. Exactly 260 replacement case/section judgments were authored,
52 per case, with frozen hashes and verbatim quotes.

Completeness rule `FIX3_PREREQUISITE_COMPLETE_SAFE_CORRECTIVE_V2` requires all
factual prerequisites plus all factual corrective objectives, materially
compatible target/state evidence, and no contradiction, silent state
assumption, unsupported account fact, or forbidden promise/action. Non-factual
control-plane boundaries do not require KB quotes. All five replacements pass:
their requested resolutions remain unsupported and no prerequisite-complete
safe correction exists.

Status is `A2_FIX3_PASS_A_V3_READY_FOR_SENIOR_REVIEW` internally and
`PASS_A_V3_REPLACEMENT_FEASIBILITY_PASS_AWAITING_SENIOR_REVIEW` externally.
Focused retained/new tests pass 66/66. Full Pass B and Pass C remain not
created; candidate inference, A3, and EV2 remain unexecuted/unauthorized; W3 P0
and W4 remain blocked. Production/KB bytes are unchanged. No stage, commit, or
push occurred. Notebook requirement is false for FIX3.

## W3-003-EV2-A2-FIX2A HARD/SAFE_CORRECTIVE consistency audit — 2026-08-21

Senior rejected FIX2's treatment of control-plane and epistemic boundaries as
if every boundary required a literal KB factual quote. FIX2A did not modify
Pass A v2, whose SHA-256 remains
`71a353f79f3a5bbdbf8faf61b63b08f842046f1082d32c3e995feaf928d146d3`.
It reused only the existing FIX1B/FIX2 semantic judgments: 52 per current HARD
case and 624 current case-section judgments total. No section was re-reviewed
or relabeled.

The deterministic taxonomy separates `CONTROL_PLANE_BOUNDARY`,
`FACTUAL_CORRECTIVE_OBJECTIVE`, and `REQUESTED_FACTUAL_RESOLUTION`. A
non-factual refusal, prohibited-action limit, no-guarantee boundary, or live-
state epistemic limit does not require a KB quote. Every banking state,
timeline, action, trace, retry, review, or handoff claim still requires exact
eligible KB support. The same completeness rule was applied to all 12 cases;
the 24/18/12/6 distribution was not used to preserve conclusions.

Seven current HARD cases remain valid: H01, H02, H05-R1, H06-R1, H10, H11,
and H12. Five conflict: H03, H04, H07, H08-R1, and H09. H03 has the same
boundary-plus-grounded-failed-transfer-handling pattern as SAFE_CORRECTIVE C18.
H04 can refuse third-party alteration at the control plane while grounding the
pending-not-completed state and wait/review path. H07 can bound live recipient
account knowledge and provide a conditional masked trace. H08-R1's live-ledger
bound is control-plane only; the five-day conditional reversal path and masked
ledger review are factually complete. H09 can bound live ATM settlement
knowledge and state the supported one-day review window.

The honest conflict count and required future replacement count are both five.
No replacement rows were authored. Status is
`A2_FIX2A_HARD_SAFE_CONSISTENCY_READY_FOR_SENIOR_REVIEW`. Pass A v2 remains
`NOT SENIOR APPROVED`; full Pass B is `NOT STARTED`; A3 is blocked; EV2 is
`NOT EXECUTED / NOT CONSUMED`; W3 P0 and W4 remain blocked. Focused tests pass
51/51. Notebook requirement is false because this is semantic taxonomy/gold
integrity work; the frozen EV2-R1 reporting point still requires the notebook.

## Historical W3-003-EV2-A2-FIX2 bounded Pass A v2 replacement — 2026-08-21

Senior authorized replacement of exactly retired H05/H06/H08 after FIX1B. The
Rev1 Pass A is byte-preserved at
`data/evaluation/w3_003_ev2_pass_a_rev1_pre_replacement.jsonl`, SHA-256
`9ef421327ba03eb12b006e857b2abb6540d6036b27a8891a491caf3660e7b567`.
Active Pass A v2 replaces only those three IDs with H05-R1/H06-R1/H08-R1 and
has SHA-256 `71a353f79f3a5bbdbf8faf61b63b08f842046f1082d32c3e995feaf928d146d3`.
All 57 other rows are canonical-hash equal and raw-line byte-equal to Rev1.

The three replacement rows were candidate-output blind and frozen before
section review. Independent review completed 156 unique judgments, exactly 52
per replacement, with eligible-section hashes and verbatim quotes. All three
pass: H05-R1 is prohibited failed-transfer audit-record deletion with no
target-compatible refusal/preservation/handoff; H06-R1 is an unresolved
pending-versus-reversed card conflict supported by five contradiction clauses;
H08-R1 asks for a live reversed-card ledger-return decision that the general KB
cannot determine and for which no complete safe correction exists.

Pass A v2 remains 60 rows with 60 unique IDs/families and 24/18/12/6 strata.
HARD reason-family counts are 3 no-approved, 2 prohibited, 3 account-specific,
and 4 genuine-conflict. Exact/normalized duplicates, direct KB sentence copies,
and A1 development-family collisions are zero; consumed collision status stays
`NOT_ESTABLISHED_PENDING_A3_FINGERPRINT_ONLY_AUDIT` with
`CONSUMED_CASE_LEVEL_FRESHNESS_LIMITATION`.

Status is `PASS_A_V2_REPLACEMENT_FEASIBILITY_PASS_AWAITING_SENIOR_REVIEW`.
Focused retained/new tests pass 42/42. Active Rev1 Pass B/C remain invalid
historical artifacts and are not current gold. No full Pass B, Pass C, candidate
inference, EV2 execution/consumption, production/KB edit, stage, commit, or push
occurred. A3, W3 P0, and W4 remain blocked.

## W3-003-EV2-A2-FIX1B exhaustive hard-abstain conflict sweep — 2026-08-21

Senior confirmed H05 and authorized a diagnostic-only sweep of all 12 frozen
HARD_ABSTAIN cases against all 52 eligible approved/effective KB sections.
FIX1B completed exactly 624 unique case/section judgments, 52 per case, with
frozen content hashes, exact supporting/contradicting quotes, and no candidate
fields, ranking, desired evidence, or heuristic label assignment. The validator
mechanically reproduces all 12 case conclusions; 28 focused FIX1/FIX1B tests
pass, including seven required FIX1B mutation classes.

Nine cases remain valid: H01, H02, H03, H04, H07, H09, H10, H11, and H12.
Three cases conflict: H05, H06, and H08. H05 retains the Senior-confirmed
reversal safe path; H06 has complete masked-reference, never-credentials, and
immediate-security alternatives; H08 has three independent complete
no-exact-release-promise plus three-day-review alternatives. H04 remains valid:
ordinary pending guidance neither covers the third-party target nor explicitly
refuses unauthorized third-party state alteration.

Reason-family valid/conflict counts are 3/0 for
`NO_APPROVED_COMPLETE_SUPPORT`, 1/2 for
`PROHIBITED_RESOLUTION_NO_COMPLETE_SAFE_ALTERNATIVE`, 2/1 for
`ACCOUNT_SPECIFIC_DECISION_UNRESOLVED`, and 3/0 for
`GENUINE_CONFLICT_OR_INSUFFICIENCY`. The frozen KB appears capable of at least
two valid cases in each family; the prohibited family conclusion is medium
confidence and requires bounded reauthoring, not forced 3/3/3/3 preservation.

Status is `A2_FIX1B_HARD_CONFLICT_SWEEP_READY_FOR_SENIOR_REVIEW`. Pass A and
active invalid Rev1 Pass B/C remain byte-unchanged; no full Pass B or Pass C was
created. A3/EV2 remain blocked and unexecuted/unconsumed; W3 P0 and W4 remain
blocked. No production source, stage, commit, or push occurred.

## W3-003-EV2-A2-FIX1 independent support-integrity correction — 2026-08-21

Senior correctly rejected A2 Rev1 as independent semantic support proof. Its
3,120 rows were structurally exhaustive but their labels and obligation mapping
were generated from preselected support plans plus intent/domain heuristics.
The five core Rev1 artifacts are byte-preserved under
`*_rev1_invalid_independence`; Rev1 is invalid for STANDARD, SAFE_CORRECTIVE,
HARD_ABSTAIN, Pass C, or A3 claims.

FIX1 kept Pass A byte-identical at
`9ef421327ba03eb12b006e857b2abb6540d6036b27a8891a491caf3660e7b567`, removed
the semantic-authoring heuristic, and added a validator/deriver that requires
content hashes and verbatim evidence quotes. Twenty focused integrity tests
pass, and the active Rev1 matrix is intentionally rejected by the new schema.

Independent review of all 52 eligible sections then found a frozen Pass A
stratum conflict in `EV2-A2-H05`. Although H05 claims
`PROHIBITED_RESOLUTION_NO_COMPLETE_SAFE_ALTERNATIVE`, the approved reversal
state rule, five-day return policy, and masked ledger-review handoff form a
complete safe corrective path. FIX1 stopped without changing Pass A or creating
a replacement Pass B/Pass C.

Status is `A2_FIX1_PASS_A_STRATUM_CONFLICT`. A3/evaluation remain blocked; EV2
is not executed or consumed; W3 P0 and W4 remain blocked. No production source,
stage, commit, or push occurred.

## W3-003-EV2-A1-R2 post-TB1 recheck — 2026-08-21

Senior accepted TB1 for an A1 recheck and subsequently approved publication.
Remote main is `8492659a50fe00f066f9f64d8759d544356b3a41`; TB1 routing hash is
`f13e3f4b0f1dac22fb1a12d9a6094bf63c52b463b2b2b6325b3c3536908beea5`, and
the other four production identities, runtime inputs, fixtures, and evaluator
matched their reviewed bytes. FIX1 active PRIMARY/summary/manifest were copied
byte-for-byte to `*_fix1_pre_tb1` historical paths before active A1 artifacts
were regenerated.

The candidate is `SENIOR_APPROVED_REMOTE_PUBLISHED_TB1_A1_R2_CANDIDATE`,
byte-frozen, committed, pushed, and remote verified. PRIMARY passed 15/15 with zero hard counters. One
REPRODUCTION passed 15/15 with matching fixture IDs/order and deterministic
semantic projection. A1 status is `IMPLEMENTED / DEVELOPMENT PRECHECK PASS /
SENIOR APPROVED / PUBLISHED / REMOTE VERIFIED`; that closure authorized A2
authoring only. W3 P0/W4 remain blocked. No consumed evidence was accessed.

## W3-003-EV2-A1-TB1 bounded target-binding repair — 2026-08-21

TB1 repaired only the confirmed same-domain target-binding defect in
`routing_v3.py`. The old CHECKS predicate accepted an account-target sentence
when any account-equivalent token was present, even when the actual check object
was mobile-device registration. A narrow conflict predicate now rejects the
known mobile-device registration/profile/settings and customer-profile setting
objects while preserving direct recipient-account detail/information checks and
generic target-unspecified checks.

The exact new regression and a negative/positive compatibility matrix failed
before the source change (four assertion failures) and passed 2/2 test methods
after it. Focused remediation passed 22/22, safe V3 passed 24/24, RED1 boundary
passed 5/5, and the non-consumed W3-003 development replay passed 14/14 with
unchanged normalized hash
`285bcc3187eeb7252cbe9f4c9d61fca00fc57af8cba873ae83e4b2df72ca4a6a`.

Status is `IMPLEMENTED / DEV REGRESSION VERIFIED / AWAITING INDEPENDENT SENIOR
REVIEW`. The existing A1 PRIMARY remains the pre-repair 14/15 failure record;
no A1 precheck/reproduction, A2, EV2 authoring/inference/execution, or consumed
data access occurred. W3 P0 and W4 remain blocked. A recheck requires a separate
Senior authorization.

## W3-003-EV2-A1 development-only precheck — 2026-08-21

The final EV2 product-gate contract was preregistered and bound to the published
RM2 production identity. The 15/15 development-only fixture structure and all
candidate/config/KB hashes verified. PRIMARY then failed closed: `EV2DEV-04`
produced a `STANDARD` response from high-overlap wrong-target device evidence,
and `EV2DEV-12` produced `ABSTAIN_ESCALATE` instead of the required approved
safe corrective alternative. `wrong_target_authorization=1`.

Status is `PRECHECK_FAIL_BLOCK_EV2_AUTHORIZATION`. Reproduction was not run;
EV2 cases were not authored or inferred; no consumed case-level material,
production source, classifier, retriever, KB, threshold, staging, commit, or
push was touched. This is development regression evidence only, not product
approval. W3 P0 and W4 remain blocked pending independent Senior review.

## W3-003-EV2-A1-FIX1 evaluator-integrity correction — 2026-08-21

REV1 was byte-preserved but cannot establish a causal RM2 verdict because its
evaluator inferred wrong-target authorization from route/risk labels. FIX1
persists raw candidate output before verifier-only semantic checks and derives
all safety counters from row verdicts. Corrected PRIMARY passed 14/15. It
confirmed exactly one target-binding defect: `EV2DEV-04` answered a recipient
account-check query with the forbidden `MOBILE_DEVICE_REGISTRATION_CHECK`
semantic target; `wrong_target_authorization=1` and `unsafe_factual_answers=1`.

`EV2DEV-12` now correctly reaches `PRIVATE_OR_INTERNAL_TARGET_BLOCKED` and a
complete `SAFE_CORRECTIVE` plan, so REV1's earlier low-direct-support result is
not a confirmed corrective-discovery defect. Status is
`PRECHECK_FAIL_CONFIRMED_TARGET_BINDING_DEFECT`; reproduction did not run. That
statement is the pre-TB1 A1 evidence status. TB1 later repaired the confirmed
defect under its separate bounded contract, but no A1 recheck was authorized.
W3 P0, EV2, A2, and W4 remain blocked.

## Active objective

The historical RCV1 predecessor contained a previous-session
`VERIFICATION_BOUNDARY_BREACH / CONSUMED_HOLDOUT_READ`. The previous W3-001
result is invalid. The RED1 production candidate was quarantined by exact
four-file identity, and no credible evidence of a post-access production edit
was found; the audit is explicitly limited by the absence of an authoritative
incident timestamp or complete prior command log.

The RCV1 verification-only helper requires the exact original non-locked
W3-001 development membership and nine hash-bound paths, rejects consumed/EV1/
unknown memberships before open, and avoids the broader W2 mapping. Boundary
tests pass 5/5 with zero forbidden opener calls. Focused RED1 passes 20/20 and
the RCV2 safe V3 allowlist passes 24/24, including the mandatory legacy
fail-closed regression. W3-003 passes 14/14 twice with identical hashes; W3-001 clean
development passes the acceptance target with 7/10 safe STANDARD answers,
3 abstentions, 10/10 safe probes, and identical two-run hashes. All four RCV2
production identities are frozen; only `pipeline_v3.py` changed
from RCV1 to fail close the legacy helper before I/O. The other production
identities and clean semantic hashes remain equal to RCV1.

RCV2/RPF1 publication is not product approval. RM2 is closed, but the next
engineering lifecycle is **new independent product-evaluation authoring**, not
Week 4. That product gate must be separately authored, frozen before execution,
independently reviewed, explicitly authorized, not tuned against EV1, and run
only once after authorization. W3 P0 remains `BLOCKED / REMEDIATION REQUIRED`
until that gate passes; W4 remains `BLOCKED`.

EV1 completed as a one-shot independent 60-case lifecycle and its frozen evidence
was published at E1 `9233289e1b330b1818d34e22c0fc641ce0f3d63a`. Independent
Senior remote verification passed. EV1 integrity is `ACCEPTED`; its product
verdict is `FAIL_REMEDIATION_REQUIRED`. The evidence is `CONSUMED / IMMUTABLE`:
it must not be rerun or tuned. N1 NB1 reporting closure is complete and remotely
verified; the notebook remains a derived mentor-facing reporting artifact, not a
new evaluation.

RM1 used non-locked development evidence only and is independently Senior
accepted. Its two proven RCA clusters are: (1) top1-preemptive requested-state
adjudication, where a terminal state conflict can be declared before a later
eligible candidate directly supports the requested state; and (2) missing
end-to-end requested-objective binding in STANDARD across same-scope padding,
claim generation, and local citation verification. `NEXT_ACTION_DIRECT_ACTION_REQUIRED`
remains a supported hypothesis only. Classifier behavior as a direct V3 cause and
global thresholds as a root cause remain not established.

One excluded W2 schema-search result was transiently printed and discarded; it
was not used for diagnosis. No individual W3-003 EV1 content was accessed or
used by RM1. RM2 diagnostics/tests must use an explicit path allowlist and no
broad recursive search under evaluation-data directories.

The historical RM1 boundary required explicit RM2 authorization and non-locked
development evidence. That authorization led to the now-quarantined RED1
candidate and this RCV1 recovery. Any future independent product gate must still
be separately authored, frozen, reviewed, and authorized.

## Prior finalized-product-decision context

This section records the historical post-SRD1 state and is superseded by the
current RCV2/RPF1 status above. The technical critical-evaluation lifecycle is complete: R15-F5 is
`FINALIZED`, `verify-results` passed, and PRIMARY/REPRO behavior is identical
for 180/180 rows. Senior approved no product variant and issued
`NOT_APPROVED_FOR_PRODUCT_INTEGRATION — REMEDIATION_REQUIRED`. Current work is
limited to closing and publishing the SRD1 decision documentation. The next
engineering task is planning-only `W3-003 — Grounded RAG Behavior Remediation`,
using non-locked development evidence. Candidate Rev7 and its PRIMARY/REPRO
results remain immutable and must not be tuning data or be rerun as a fresh
holdout. W4 real AI integration remains blocked until remediation is followed
by a separately authorized independent evaluation and product verdict.

## Historical pre-evaluation objective context

Candidate Revision 7 remains frozen and Senior semantic-approved. Real E1
attempts under historical A12 exposed an offline encoder-binding defect before
any raw output was persisted. EA1 Revision 12 and A12 remain historical
committed evidence but are superseded for execution. Revision 13 binds
`HF_HUB_OFFLINE=1`, production `local_files_only=True`, and hashes the complete
18-module execution closure. Postflight found distribution count/fingerprint
raw discovery multiplicity drift. The environment-provenance remediation now
uses a canonical 298-package third-party identity (`39c1c4a0...`) that is equal
across C1/C2/C3/C4 while retaining raw 299/300/302 history diagnostically. The
authorization candidate now binds the stable environment-identity contract,
and runtime compares the live identity with the reviewed/authorized identity
before model construction. Seven environment and three source-tamper negative
controls fail closed pre-model. R13 is
`READY FOR SENIOR READINESS REVIEW`; `evaluation_authorized=false`,
`critical_evaluated=false`, and `model_verdict=NOT_ESTABLISHED`.

Senior rejected candidate revision 4 and blocked further candidate authoring
pending a contract amendment. Senior has now approved contract Option A. The
fixed 40/20 contract is not semantically
feasible with the frozen KB: 15 of the 20 proposed negatives admit a useful,
approved safe correction and only five remain true abstain/escalate cases.
Revision 4 is byte-preserved as rejected review history. The W3-002-CR1 Option A
contract amendment is `DONE / REVIEWED / COMMITTED / PUSHED` at commit
`22e8b38ae28e86537ece8aa892f39c35b517e74b`. Structural integrity and
pre-evaluation integrity are false for the rejected candidate. Semantic approval, evaluation
authorization, and critical evaluation remain false. The model verdict is
NOT_ESTABLISHED, Week 3 P0 remains BLOCKED / IN PROGRESS, and Week 4 remains
BLOCKED / NOT STARTED.

Senior semantic review returned `FIX_REQUIRED` for revision 5. Revision 5 is now
`REJECTED / PRESERVED AS REVIEW HISTORY`; its 19-artifact archive is frozen under
`reports/week_03/rejected/critical_eval_v2_revision_5/`. Candidate revision 6 is
now `FROZEN_CANDIDATE / SENIOR_SEMANTIC_REVIEW_APPROVED / COMMITTED / PUSHED` at
commit `d27de987d0eb7a942c88590eec9a30bdd6ee33d8`.
The unchanged Option A candidate contract has
40 `ANSWER / STANDARD`, 15 `ANSWER / SAFE_CORRECTIVE`, and 5
`ABSTAIN_ESCALATE` cases, with all 60 model-input byte tuples unchanged from
rejected revision 4.
Senior semantic approval has been granted for the frozen revision-6 candidate
bytes. Evaluation authorization, critical evaluation, model loading, encoder
loading, retrieval, generation, inference, and critical-pipeline execution
remain prohibited.

COV1 subsequently reviewed all 94 frozen complete covers and found 84 consistent
and ten inconsistent with the then-current EA1 sentence evaluator. Senior
adjudicated six as evaluator-rule gaps and confirmed four candidate-cover
semantic defects. Revision 6 remains immutable historical evidence and is
`SEMANTICALLY_APPROVED_AT_THE_TIME / SUPERSEDED_PRE_EVALUATION_BY_COV1`; it was
never evaluation-authorized. Candidate revision 7 removes only the four confirmed
obligation assignments, mechanically re-derives 92 complete covers, preserves all
60 model inputs and the 40/15/5 distribution. Senior verdict
`APPROVE_SEMANTIC_INTEGRITY — CANDIDATE REVISION 7` establishes external
semantic approval for the frozen bytes. Those exact 37 reviewed paths were
committed and pushed at `18a1840f39fef8f07337ff357f7991292389bae9`;
revision 7 is now `FROZEN_CANDIDATE / SENIOR_SEMANTIC_REVIEW_APPROVED /
COMMITTED / PUSHED`.

The Senior-approved decision bundle has SHA-256
`bc7317000005859f2e4b215cf0c4f687e5e284a4a004270d81f9f5abd0074786`.
The approved contract keeps `ANSWER` and `ABSTAIN_ESCALATE` as top-level response
types and adds `answer_subtype=STANDARD|SAFE_CORRECTIVE`. The distribution is 40
`ANSWER / STANDARD`, 15 `ANSWER / SAFE_CORRECTIVE`, and 5
`ABSTAIN_ESCALATE`. At the contract-amendment milestone this package did not
create or authorize candidate revision 5; the later, separately reviewed
authoring contract was the sole authorization for revision 5, while the Senior
`FIX_REQUIRED` correction contract separately authorized revision 6.

## Historical W3-002-CR1 authoring boundary

The lifecycle booleans below describe the pre-evaluation authoring milestone.
They are preserved as historical evidence and are superseded for current
operational status by the SRD1 section at the end of this file.

- Contract-amendment task: DONE / REVIEWED / COMMITTED / PUSHED
- Contract-amendment commit: `22e8b38ae28e86537ece8aa892f39c35b517e74b`
- Evaluation version: `critical_eval_v2`
- Evaluation as-of date: `2026-07-28`
- Candidate objective: 60 new queries, 3,120 independent eligible-section
  judgments, obligation-derived mappings, and pre-evaluation integrity evidence
- Candidate revision 1: REJECTED — PASS B WAS GENERATED FROM EMBEDDED ANSWER KEYS
- Candidate revision 2: REJECTED / SEMANTIC_AND_VERIFIER_CORRECTION_REQUIRED
- Candidate revision 3: REJECTED / SEMANTIC_DESIGN_CORRECTION_REQUIRED
- Candidate revision 4: REJECTED / PRESERVED AS REVIEW HISTORY
- Contract amendment: OPTION A / SENIOR APPROVED
- Contract distribution: 40 STANDARD / 15 SAFE_CORRECTIVE / 5 ABSTAIN
- Candidate revision 5: REJECTED / PRESERVED AS REVIEW HISTORY
- Candidate revision 6: HISTORICALLY_SEMANTICALLY_APPROVED / SUPERSEDED_FOR_EVALUATION_BY_COV1
- Candidate revision 7: FROZEN_CANDIDATE / SENIOR_SEMANTIC_REVIEW_APPROVED / COMMITTED / PUSHED
- Candidate revision 7 commit: `18a1840f39fef8f07337ff357f7991292389bae9`
- EA1 readiness revision 7: REJECTED_BY_SENIOR / SAFETY_AND_AUTHORIZATION_HARDENING_REQUIRED
- EA1 readiness revision 8: REJECTED_BY_SENIOR / DISCLOSURE_TARGET_COVERAGE_INCOMPLETE / ADVERSARIAL_FIXTURE_TARGET_CONSTRUCTION_INVALID
- EA1 readiness revision 9: FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_AUTHORIZATION_REVIEW
- EA1 readiness revision 12: SENIOR EXECUTION READINESS APPROVED / COMMITTED / PUSHED
- Candidate package: FROZEN / STRUCTURAL ONLY
- Candidate bytes frozen: true
- Structural integrity verified: true
- Pre-evaluation integrity passed: true
- Pre-evaluation integrity scope: STRUCTURAL_ONLY_SEMANTIC_APPROVAL_PENDING
- Candidate manifest SHA-256: `f912798ae5c02c774702ae97bee8b2b4f6c6ab12b6534e1b2a3817a969b905ef`
- Senior semantic review approved: true for candidate revision 7 via separate Senior record
- Evaluation authorized: true for the exact committed Candidate Revision-7 and reviewed R2 execution bytes
- Critical evaluated: false
- Model/pipeline verdict: NOT ESTABLISHED
- `senior_semantic_review_approved=true`
- `evaluation_authorized=true`
- `critical_evaluated=false`
- `model_verdict=NOT_ESTABLISHED`
- Week 3 P0: BLOCKED / IN PROGRESS
- Week 4: BLOCKED / NOT STARTED

The frozen revision-7 candidate manifest retains its author-time
`senior_semantic_review_approved=false` and
`pre_evaluation_integrity_scope=STRUCTURAL_ONLY_SEMANTIC_APPROVAL_PENDING`
fields. Current Senior semantic approval is established separately by
`critical_eval_v2_revision_7_senior_semantic_approval.json`; it does not
authorize evaluation.

The rejected revision-6 EA1 work was used only as verified reference
architecture. The revision-7 rebind authored all six COV1 evaluator-only
alternatives without changing candidate bytes. The initial 92/96 stop was a
definition mismatch: the candidate freezes 92 minimum-cardinality canonical
covers, while the evaluator also exposes four valid larger inclusion-minimal
alternatives. Corrected production and independent brute-force derivations agree
on 55/55 answerable queries and all 92 canonical covers. The larger covers remain
explicit diagnostics. EA1 is `FROZEN_READINESS_PACKAGE /
AWAITING_SENIOR_AUTHORIZATION_REVIEW`; this does not authorize evaluation.

Senior subsequently rejected EA1 readiness revision 7 while retaining Candidate
Revision 7 as frozen and semantically approved. The rejected readiness ZIP is
preserved externally at SHA-256
`dc72ab6d074c3dd3eb3391586ec783c8b287abbb44114e872e048c4cf5c9757c`.
Readiness revision 8 adds deterministic target-first negative morphology,
payload-before-target and negative-status-with-payload detection, occurrence-local
precedence, 22/22 exact Senior safety regressions, a 206-case expanded matrix
with zero FP/FN, 27 observed mutation rows, eight real self-adversarial cases,
today-only authorization daily-path topology, and occurrence-level stale-binding
classification. Candidate Revision 8 remains absent.

Senior subsequently rejected EA1 readiness revision 8 for incomplete disclosure
target coverage and invalid adversarial fixture target construction. Its external
review ZIP is preserved at SHA-256
`3291975173dff7e8afb0da4ab368d32e8f1913020bc9951f5e56b3b8686fe218`.
Readiness revision 9 explicitly classifies all 15 SAFE_CORRECTIVE cases, binds
eight disclosure-capable queries to 11 canonical disclosure targets, validates
176 disclosure fixtures before evaluator execution, and expands the complete
matrix to 256 cases with zero malformed fixtures and zero FP/FN. Exact Senior
regressions pass 38/38, including all ID02/ID03/ID04 payload-order forms; 30
observed mutations fail at their expected layers and eight independent
self-adversarial categories pass. Candidate revisions 8 and 9 remain absent.

Revision 1 manifest SHA-256 is
`39af29f929ef9a9287808c26d62787079e376a8b7ac05847fa10729d27374b99`.
Its support plan, judgments, mapping, negative audit, and forbidden audit remain
byte-preserved under explicit `revision_1_rejected` paths. Revision 2 contains
3,120 content-bound standalone judgments: 92 DIRECT, 20 PARTIAL, 1,390
CONTEXTUAL, 9 CONTRADICTION/OUTDATED, and 1,609 IRRELEVANT. It derives 16 hard
negatives, two multi-section cases, zero multi-document cases, zero outcome
changes, and zero false-abstain findings. These remain candidate semantics until
Senior review.

Revision 2 rejected manifest SHA-256 is
`668992392f3e0f4addeb017a0028f6bc676614910d0e1c03fb8f3e3c51a20834`;
its external review bundle SHA-256 is
`e0a447f7a71f6dc125d87dad088889d779de2c3c8892e7167d11b9a8b3b38a56`.
All 17 preserved revision-2 files live under
`reports/week_03/rejected/critical_eval_v2_revision_2/`.

Revision 3 rejected manifest SHA-256 is
`650a8a5847d83211c96941e549bc4379df89e1ae91c857a59c65160a6ed0f688`;
its review bundle SHA-256 is
`6e32aa4081c609fb8e2767c099af419f046cd6c6261aec39ddd11368a426603a`.
All 18 revision-3 files are byte-preserved under
`reports/week_03/rejected/critical_eval_v2_revision_3/`.

Revision 4 rejected manifest SHA-256 is
`b2b021c78f11ff4cf5d023044b464b43d806f0c0217fd8e3b196dfc736bb52af`;
its rejected review bundle SHA-256 is
`a081e909113a682e7790b758f2b90bea3eea26025103e7209dc1c32e8f04fa5e`.
All 19 revision-4 artifacts remain byte-preserved under
`reports/week_03/rejected/critical_eval_v2_revision_4/`. Candidate revision 5 now
exists separately at active-root paths and does not modify that archive.

Revision 5 rejected manifest SHA-256 is
`342e5652fb03f249eeb999f7b2c4452668b82ce83d28d65b9a3d452745cc2d32`;
its rejected review bundle SHA-256 is
`9599c09bac7d1b46c9d4893c546993958f40f64805db1b7fb8a97625b966debf`.
All 19 revision-5 artifacts are byte-preserved under
`reports/week_03/rejected/critical_eval_v2_revision_5/`.

## W3-002-CR1 approved contract amendment

- Senior verdict: `APPROVE_CONTRACT_AMENDMENT — OPTION A`
- Lifecycle: DONE / REVIEWED / COMMITTED / PUSHED
- Committed SHA: `22e8b38ae28e86537ece8aa892f39c35b517e74b`
- `senior_contract_amendment_approved=true`
- `contract_amendment_option=OPTION_A`
- `contract_amendment_distribution=40_STANDARD_15_SAFE_CORRECTIVE_5_ABSTAIN`
- Contract decision bundle SHA-256:
  `bc7317000005859f2e4b215cf0c4f687e5e284a4a004270d81f9f5abd0074786`
- Revision 4: REJECTED / PRESERVED AS REVIEW HISTORY
- Revision 5 at contract-amendment commit: NOT CREATED
- Current revision 5: REJECTED / PRESERVED AS REVIEW HISTORY
- Revision 6 historical milestone: FROZEN_CANDIDATE / SENIOR SEMANTIC REVIEW APPROVED / COMMITTED / PUSHED
- Revision 6 commit: `d27de987d0eb7a942c88590eec9a30bdd6ee33d8`
- Revision 6 manifest SHA-256: `2f42fb4ff7159ef2735ce88418b0dbfcc414b0091476f1882a83d13e807002ad`
- Revision 6 semantic review approved at that milestone: true
- Evaluation authorized: false
- Critical evaluated: false
- Model verdict: NOT_ESTABLISHED
- Week 3 P0: BLOCKED / IN PROGRESS
- Week 4: BLOCKED / NOT STARTED

The amended taxonomy has top-level `ANSWER` and `ABSTAIN_ESCALATE`, with
`STANDARD` and `SAFE_CORRECTIVE` subtypes only for answers. The 20-case slice is
named **safety challenge cases**, not negative abstention. Contract approval is
not candidate semantic approval.

## W3-002 integrity incident evidence

- Senior review verdict: APPROVE_COMMIT — INTEGRITY INCIDENT EVIDENCE
- Implementation: DONE / REVIEWED / ACCEPTED
- Original numerical run: DONE / PRESERVED AS HISTORICAL DIAGNOSTIC EVIDENCE
- Original evaluator-reported result: FAILED UNDER INVALID MAPPING CONTRACT
- Critical-set integrity: INVALIDATED — PRE-EVALUATION MAPPING AUDIT WAS SELF-REFERENTIAL
- Model/pipeline verdict: NOT ESTABLISHED
- Independent post-hoc scope audit: 40 positives and 20 negatives, each with 52
  unique eligible-section judgments
- Positive mapping defects: 20
- Hard negatives that directly support their query: 2
- Over-constrained original exact-ID/document mappings: 6
  - single section sufficient: `Q_CRIT_A_003`, `Q_CRIT_A_020`, `Q_CRIT_A_040`
  - two semantic sections required but one approved escalation document sufficient:
    `Q_CRIT_A_016`, `Q_CRIT_A_028`, `Q_CRIT_A_036`
- Semantically multi-document necessary: 0; no reviewed critical query was proven
  to require evidence from two distinct documents
- False ABSTAIN labels: 8
- Integrity incident analysis: DONE / REVIEWED / ACCEPTED
- Replacement critical evaluation: NOT CREATED

## Current versions
- Pre-W3-001 committed code baseline: W2-003 commit
  `a886e56143d80e5c70ddbae3507921aeed071dbb`
- Historical W1-004 commit:
  `7c60110eab7cd18e538b274803f31879179d9e46`
- Banking77 protocol: `banking77_w1_v1`
  - upstream revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`
  - train/validation/test: 8,998 / 1,005 / 3,080
  - membership SHA-256: `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`
- W1-004 evaluation config SHA-256:
  `a6ac09654884528aa6ccabf784a349304eddecb3ccb0add680000ad4f6272a40`
- Frozen lexical candidate: `lexical_word_unigram`
  - validation accuracy/macro-F1: 0.865672 / 0.862649
  - official-test accuracy/macro-F1: 0.878247 / 0.878362
- Frozen semantic candidate: `semantic_all_minilm_l6_v2`
  - encoder revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
  - validation accuracy/macro-F1: 0.900498 / 0.898020
  - official-test accuracy/macro-F1: 0.908117 / 0.908075
- Selected downstream intent model: `semantic_all_minilm_l6_v2`
  - config: `configs/models/banking77_semantic_w1.json`
  - config SHA-256: `de4ebff80c7e758339def8b35a31e4c3e5b7723b2e2eec8493e818ae8887b50b`
  - fallback: `lexical_word_unigram`
- Official frozen test: EVALUATED under W1-004; no post-test tuning
- KB version: `payresolve_synthetic_kb/kb_v1` — CONTENT FROZEN; VALIDATOR FIX VERIFIED
  - evaluation as-of date: `2026-07-28`
  - documents/eligible: 36 / 26
  - canonical dataset SHA-256:
    `e54a21529c516659265f82ca4818e1c844c05e8e7d7a692b02154115869d4c88`
  - config SHA-256:
    `d6ff1adc158c41cd6e9c9a418aa22bd2696cd0be80343a174b3f74146f74a909`
  - schema SHA-256:
    `ee9f959cef795b35482db4f0a9868f5981ec8291e3f228d63a289fddeae3dc29`
- Retrieval benchmark: `W2-003/kb_v1_r0_r1` — DONE / REVIEWED / ACCEPTED
  - candidate corpus: 26 documents / 52 section chunks
  - encoder: frozen normalized 384D MiniLM revision `1110a243...9b4d41`
  - R1 selected development lambda: 0.15
  - locked decision: retain R0
- Gold mapping: `payresolve_gold_evidence_mapping/gold_mapping_v1` — REVIEWED / ACCEPTED / FROZEN
  - evaluation as-of date: `2026-07-28`
  - queries: 60 (10 development / 50 locked test)
  - response types: 50 ANSWER / 10 ABSTAIN_ESCALATE
  - scenario/query/mapping SHA-256:
    `97cdf1ae69b280af14043e987452040db925c3e93acb869c1072dfb4cb32c486` /
    `73d65c1209beac734123b9d1421f1fdefe32330712e4fe9359f26b7c620345aa` /
    `4ed85198ac1929ea40356fb86d0e959ea81d8c3630aff405ac04e6540160069c`
- Evidence Gate v2: `W3-001-CR1/grounded_pipeline_v2` — UTILITY RECOVERED WITH ZERO OBSERVED SAFETY VIOLATIONS / REVIEWED / ACCEPTED
  - selected policy: `S0.40_C0.20` (top-1 0.40, canonical support 0.20,
    ambiguity gap 0.03)
  - pipeline config SHA-256:
    `9319799a704ddbc82e824f7351adc3852672e4b277efea2fc0bc552ef4f518f2`
  - selection SHA-256:
    `b17cee0c976552d14eec940f9bb81d95bb2ba9731b615295ab6be10313606469`
  - holdout raw/membership/mapping SHA-256:
    `6ea54ec1dd79987dcee329a200d6258629050944eabc238d8527581a2b968af8` /
    `1b7c149a9c0f1eb4cbe524ef820e5cc4985d9c6cc5e6e7604463f41a5147ee2f` /
    `42ae758031d1fb682f4fb20da0060a92e5a69905830a5be1a4b578beb7d5f178`
  - mapping audit/overlay/adjudicated mapping SHA-256:
    `4c90728a06652918ae64d8919aa4fa2cd6d17bf4f94ebb9e881acd172bee3cdd` /
    `dd45753d9a0a39023a6b915c097ff4e5601927771f42834593e4094e8460d14c` /
    `029a06087b4a7f15f13c61c7a0bb2cf9c76f740448f9715bdd47e6dfc9a7fcf3`

## Completed
- [x] Repository bootstrap and reporting workflow
- [x] W1-001 authoritative source, audit, and deterministic locked split
- [x] W1-002 frozen lexical validation baseline
- [x] W1-003 frozen semantic validation baseline
- [x] W1-004 official-test benchmark, error analysis, model selection, and gate
- [x] Week 1 P0 gate passed
- [x] W2-001 controlled synthetic KB — DONE / REVIEWED / COMMITTED / PUSHED
- [x] W2-002 gold evidence mapping — DONE / REVIEWED / COMMITTED / PUSHED
- [x] W2-003 retrieval R0/R1 — DONE / REVIEWED / COMMITTED / PUSHED
- [x] Week 2 P0 gate passed
- [x] W3-001 implementation — DONE / REVIEWED / ACCEPTED; overall — PARTIAL / REVIEWED / ACCEPTED
- [x] DOC-002 mentor sprint-report Markdown draft — DONE; no technical gate changed
- [x] DOC-003 mentor sprint-report XLSX — DONE; source template preserved and no technical gate changed
- [x] W3-001-CR1 implementation — DONE / REVIEWED / ACCEPTED; post-hoc adjudicated evaluation — PASS / REVIEWED / ACCEPTED
- [x] W3-002 execution package and integrity incident — DONE / REVIEWED / ACCEPTED; critical set INVALIDATED; model verdict NOT ESTABLISHED

## Latest verified evidence
- Official test contains 3,080 rows, all 77 intents, exactly 40 rows per intent.
- Lexical: accuracy 0.878247, macro-F1 0.878362, 2,705 correct, 375 errors.
- Semantic: accuracy 0.908117, macro-F1 0.908075, 2,797 correct, 283 errors.
- Semantic deltas: accuracy +0.029870 and macro-F1 +0.029713.
- Paired outcomes: 2,611 both correct, 94 lexical-only, 186 semantic-only,
  and 189 both wrong.
- Per-class F1: semantic improved 49, regressed 21, unchanged 7; no regression
  reached absolute 0.20.
- Both models correctly classified all seven normalized-overlap rows; excluding
  them changes either aggregate metric by less than 0.0003.
- Primary/repro stable outputs were byte-identical; CPU runtimes varied as expected.
- W1-004 artifact validator passed with test encoded/evaluated recorded true.
- W2-001 validator passed: 36 schema-valid English synthetic documents, with
  APPROVED/DRAFT/EXPIRED counts 26/5/5 and eligible count 26.
- All 10 locked intents have at least two eligible documents and two document
  types; exact `reverted_card_payment?` maps to safe slug
  `reverted_card_payment`.
- Four complete version families and 12 explicit hard-negative relationships
  passed reference and lifecycle validation.
- First-28 quality gate passed with 20 eligible documents, complete coverage,
  four version families, and nine fully resolved hard-negative relationships.
- Exact/normalized duplicate groups and token-Jaccard candidates at threshold
  0.72 were both zero; manual review completed.
- Senior-review hardening closed the schema/lifecycle/hard-negative false-pass
  defect without changing canonical KB bytes. All nine direct mutations fail
  with explicit error codes; the first-28 gate counts only valid structures.
- W2-001 focused tests passed 29/29; full repository suite passed 56/56; project
  reporting validator passed.
- W2-002 validator passed with 60 unique queries, exact 10/50 split and 50/10
  ANSWER/safety distribution; all 26 eligible and all 10 ineligible documents
  are represented in their permitted roles.
- Locked ANSWER cases cover 26 normal, 10 hard-negative, four multi-document,
  three short, and four version-sensitive tags. Section role counts are
  56 gold / 50 acceptable / 50 hard-negative / 10 forbidden.
- Query duplicate, normalized duplicate, Banking77 train/test equality, and
  high-threshold lexical-overlap audits all returned zero candidates/overlaps.
- Senior review superseded the initial 60/60 construction acceptance: 19 gold
  and 19 acceptable roles changed, two ANSWER queries and ten safety probes were
  rewritten, and all 60 rationales now state direct-support or no-evidence facts.
- Senior v2 re-review accepted every other correction and found one residual
  role inversion in `Q_LOCK_CASH_PEND_002`; FAQ state evidence is now primary
  and the runbook recognition gate is acceptable support.
- Senior final review verdict: `APPROVE_COMMIT`.
- W2-002 focused tests passed 43/43; seven direct mutations failed as expected;
  the full repository suite passed 99/99.
- W2-003 corpus contains 26 eligible documents and 52 deterministic section
  chunks, with zero DRAFT/EXPIRED/future-effective candidates.
- Development selected lambda 0.15 from the frozen positive grid; dev strict
  MRR@3 was 0.300000 for R0 and 0.400000 for selected R1.
- Locked R0 strict Hit@1/Recall@3/MRR@3 were
  0.350000/0.616667/0.483333; R1 were 0.325000/0.566667/0.454167.
- Paired first-gold outcomes were 3 WIN / 4 LOSS / 33 TIE for R1; R1 broke one
  R0 top-1 success and corrected none. R0 is retained by the frozen rule.
- Complete gold coverage@3 was 0.575 for R0 versus 0.525 for R1. All DRAFT,
  EXPIRED, wrong-status, and forbidden-evidence leakage metrics were zero.
- Frozen classifier diagnostic accuracy was 33/60 (0.55); confidence remains
  uncalibrated and diagnostic only.
- Primary and reproducibility rerun shared stable SHA-256
  `64637a8ca56cf8ac9a3368118f7b0df3eb3599f66f540c77954a33a413ad40e6`.
- Senior review accepted the locked metrics/R0 decision and required evidence
  hardening. The corrections preserve all seven accepted numerical artifact hashes.
- Development audit persists 50 rows (10 queries × five variants) and recomputes
  every frozen metric; selected lambda remains 0.15.
- Corrected analysis contains 28 ANSWER rows with specific root causes and ten
  separate safety diagnostic rows. Automatic A/C/D/E/F/G/I counts are
  3/4/4/4/2/4/7; reviewed counts are 3/4/4/4/2/3/8 after enforcing the exact
  multi-document contract.
- The final taxonomy patch corrected six false F assignments: four to D and two
  to E. F excludes strict gold itself and requires a rank-qualified non-gold
  sibling; the verifier recomputes both categories for every row.
- The four-query multi-document slice has mean gold Recall@3 0.666667 and
  complete coverage 1/4 for both R0 and R1.
- Fresh-clone tracked verification passed while ignored W2 cache and fitted model
  were temporarily unavailable; optional runtime verification also passed.
- W2-003 focused tests passed 56/56 and the full repository suite passed 155/155.
- W3-001 froze 20 development cases (10 W2 development positives and 10 new
  negative probes) with zero W2-locked or Banking77 exact/normalized overlap.
- The preregistered 12-policy grid selected `S0.40_C0.45`. Development safe
  resolution is 0.50, unsafe-answer rate is 0.00, negative abstention is 1.00,
  and positive grounded resolution recall is 0.00.
- Primary/reproduction outputs remain byte-identical. The selected run has no
  answers or claims, so citation correctness and unsupported-claim rate are
  `NOT_APPLICABLE`; controlled tests, rather than selected-run utility, prove the
  ANSWER/citation path. Corrected focused/full suites pass 69/69 and 224/224.
- Senior review lifecycle: initial implementation → Senior `FIX_REQUIRED` →
  citation metadata binding → evidence relevance metrics → non-vacuous citation
  metrics → config-driven generator weights → Senior `APPROVE_COMMIT — PARTIAL BASELINE`.
- The grounded pipeline, approved-only context boundary, extractive generator,
  claim/citation verifier, and tracked evaluation infrastructure are accepted.
  The selected evidence gate is not accepted as a useful production candidate
  because it answered zero of ten positive development queries.
- W3-001-CR1 recovered holdout utility relative to gate v1: positive grounded
  recall 0.10 → 0.60 and safe resolution 0.55 → 0.80. Gate v2 answered 7/20,
  resolved six positive cases, covered transfer/card-payment/cash-withdrawal,
  retained negative abstention 1.00, and had zero unsafe answers, unsupported
  claims, DRAFT/EXPIRED citations, or citation metadata failures.
- The original CR1 frozen-mapping evaluation remains `FAILED`: 7 answers, six
  relevant positive answers, one wrong-evidence answer, positive recall 0.60,
  safe resolution 0.80, and zero unsafe answers.
- The exhaustive audit reviewed all ten positives against all 52 eligible approved
  sections and found exactly three omitted direct-support sections (3/10).
- The Senior-approved overlay changes relevance labels only. Frozen queries,
  rankings, outputs, citations, policy, thresholds, and primary/reproduction bytes
  remain unchanged; no encoder, retrieval, or generation rerun occurred.
- Adjudicated Gate v2 has seven relevant positive answers, zero wrong-evidence
  answers, positive recall 0.70, safe resolution 0.85, negative abstention 1.00,
  and zero unsafe answers, unsupported claims, DRAFT/EXPIRED citations, or citation
  metadata failures. Status is `PASS / REVIEWED / ACCEPTED`.
- Senior final verdict: `APPROVE_COMMIT — QUALIFIED POST-HOC PASS`.
- Final adjudication verification passed: focused tests 65/65, full repository
  tests 289/289, all tracked validators, project-doc validation, and diff check.

## Risks / limitations
- Seven normalized train/test overlaps remain in the canonical official boundary.
- Thirty reviewed errors show substantial ambiguous/underspecified label boundaries;
  five are potential annotation/taxonomy issues rather than proven mislabels.
- Classifier probabilities are uncalibrated diagnostic values; thresholding and
  OOS/OOD remain P1 and were not opened.
- Semantic is materially slower on CPU and uses an ignored ~183 MB encoder cache;
  these measurements are not production latency.
- KB timelines and workflows are fictional research controls, not real policy.
- Lightweight lexical near-duplicate screening does not prove absence of semantic
  overlap.
- Gold mapping has one construction reviewer and was Senior-reviewed, but is not
  independently annotated.
- The predicted-intent boost improved development metrics but regressed all three
  strict locked metrics; this development/locked divergence limits generalization.
- The 60-query classifier diagnostic is synthetic and must not be interpreted as
  a calibrated deployment estimate.
- The selected W3-001 gate abstains on all 20 development cases. This follows the
  frozen safety-first rule but has no demonstrated development utility.
- The holdout is now a post-hoc adjudicated evaluation rather than a pristine
  untouched-label evaluation. This limitation remains explicit even though the
  exhaustive symmetric correction passes the registered safety and utility gates.

## Next 3 actions
1. Close, review, and publish the SRD1 Senior result decision record without
   modifying the finalized lifecycle or locked Revision-7 evidence.
2. Plan `W3-003 — Grounded RAG Behavior Remediation` root-cause and remediation
   work using non-locked development evidence; do not start implementation in
   this reporting task.
3. Define a new independent evaluation boundary before any product-approval
   claim, and keep W4 real AI integration blocked until that gate passes.

## W3-002-CR1-EA1 readiness revision 10 — 2026-08-11

- **Task:** `W3-002-CR1-EA1-REV10` (Week 3, P0).
- **EA1 readiness revision:** `10`.
- **Candidate Revision 7:** `FROZEN / SENIOR SEMANTIC APPROVED / COMMITTED /
  PUSHED`; immutable verification remains 23/23 at commit
  `18a1840f39fef8f07337ff357f7991292389bae9`.
- **F1 runtime subtype assumption:** `ADJUDICATED / CLOSED`.
  `observed_answer_subtype_candidate=NULL_BY_CONTRACT`; injected `STANDARD` and
  `SAFE_CORRECTIVE` both fail with `RAW_PRE_FREEZE_SUBTYPE_FORBIDDEN`. Final
  `observed_answer_subtype` is `POST_FREEZE_EVALUATOR_DERIVED`. Focused F1
  evidence: 8/8 PASS; pre-freeze `gold_loader_calls=0`.
- **F2 narrow production-bounded disclosure guard:** `CLOSED`. Registry binds
  exactly eight disclosure-capable queries and 11 canonical targets from the
  settled Revision-9 surface. All 11 targets are honestly marked
  `NO_ENUMERATED_LITERAL_VALUE`; no private value was invented. The final
  contract is `UNSAFE = parser_unsafe OR narrow_guard_unsafe`; 11/11 target
  subtests and 4/4 truth-table subtests pass. Generalized disclosure detection
  remains deferred and is not a Week-3 P0 blocker.
- **F3 row execution provenance:** `CLOSED`. The single authoritative
  `validate_raw_execution_binding` validates Candidate Revision 7,
  `execution_id`, run, variant, exact query membership, model-input SHA, and
  active execution-config SHA before raw persistence, before freeze, and before
  evaluator/gold load. Nine tamper/boundary regressions pass; invalid rows create
  no raw file, freeze manifest, or state transition.
- **Verification:** Revision-10 focused tests 20/20 PASS; settled Revision-9
  readiness tests 118/118 PASS; combined focused 138/138 PASS; related
  Candidate/Option-A/feasibility/safety tests 210/210 PASS; isolated exact-byte
  application suite 637/637 PASS with eight explicit skips; readiness and
  detached-bundle verifiers PASS. Historical Senior 38/38, matrix 256 with zero
  FP/FN, mutations 30/30, and adversarial categories 8/8 remain regression
  evidence.
- **EA1 Revision 10:** `SENIOR_REVIEWED /
  F3_BATCH_MEMBERSHIP_DEFECT_FOUND`; reason
  `RAW_BATCH_EXACT_MEMBERSHIP_NOT_ENFORCED_PRE_PERSISTENCE`.
- **Lifecycle:** `evaluation_authorized=false`, `critical_evaluated=false`,
  `model_verdict=NOT_ESTABLISHED`; Week 3 remains `BLOCKED / IN PROGRESS` and
  Week 4 remains `BLOCKED / NOT STARTED`.
- **Forbidden work not performed:** no Candidate Revision 8/9/10, runtime subtype
  router, public Week-4 schema, model/encoder/retrieval/generation/inference,
  critical evaluation, staging, commit, or push.

## W3-002-CR1-EA1 readiness revision 11 — 2026-08-11

- **Task:** `W3-002-CR1-EA1-REV11` (Week 3, P0), limited to F3 batch
  membership closure.
- **Candidate Revision 7:** frozen, Senior-approved, committed, pushed, and
  byte-verified 23/23; no Candidate Revision 8/9/10/11 exists.
- **F1/F2:** `CLOSED / REGRESSION_ONLY`; no semantic or disclosure expansion.
- **F3:** `ROW_PROVENANCE=CLOSED` and
  `BATCH_MEMBERSHIP_PROVENANCE=CLOSED`. `validate_raw_run_binding` requires
  exactly 60 rows, 60 unique query IDs, and exact set equality with the frozen
  runtime payload, then delegates every row to `validate_raw_execution_binding`.
- **Boundaries:** the same batch validator runs before raw persistence, before
  freeze, and before evaluator/gold load. F3-J through F3-N pass 5/5.
- **EA1 Revision 11:** `FROZEN_READINESS_PACKAGE /
  AWAITING_SENIOR_AUTHORIZATION_REVIEW`.
- **Lifecycle:** `evaluation_authorized=false`, `critical_evaluated=false`,
  `model_verdict=NOT_ESTABLISHED`; Week 3 remains `BLOCKED / IN PROGRESS` and
  Week 4 remains `BLOCKED / NOT STARTED`.
- **Forbidden work not performed:** no inference, retrieval, generation,
  critical evaluation, staging, commit, or push.

## W3-002-CR1-EA1 readiness revision 12 — 2026-08-12

- **Task:** `W3-002-CR1-EA1-REV12-AUTH-DATE` (Week 3, P0), limited to the
  authorization daily-report topology rollover from 2026-08-11 to 2026-08-12.
- **Candidate Revision 7:** `FROZEN / SENIOR SEMANTIC APPROVED / COMMITTED /
  PUSHED`; manifest, mapping, and Pass-B bytes remain unchanged.
- **EA1 Revision 11:** `SENIOR_EXECUTION_READINESS_APPROVED / COMMITTED /
  PUSHED / SUPERSEDED_ONLY_BY_AUTHORIZATION_DATE_TOPOLOGY_AMENDMENT` at
  readiness commit `c7bc68bbef51684f6ff4ab7a672ca78af4cbbadd`; it is not rejected.
- **EA1 Revision 12:** `SENIOR EXECUTION READINESS APPROVED / COMMITTED /
  PUSHED` as R2 `cec29477e3c75d132b54f787ba602a0a1b33f578`; reason
  `AUTHORIZATION_DAILY_REPORT_DATE_ROLLOVER`.
- **Exact future A allowlist:** authorization record, `PROJECT_STATE.md`,
  `TASKS.md`, Week-3 summary, and `daily/2026-08-12.md` only. The prior
  `daily/2026-08-11.md` path is rejected for A.
- **Closed semantics preserved:** F1, F2, F3 row provenance, and F3 batch
  membership provenance remain closed and unchanged.
- **Lifecycle:** `evaluation_authorized=false`, `critical_evaluated=false`,
  `model_verdict=NOT_ESTABLISHED`; Week 3 remains `BLOCKED / IN PROGRESS` and
  Week 4 remains `BLOCKED / NOT STARTED`.
- **Forbidden work not performed during Revision 12:** no authorization record
  A, model/encoder loading, retrieval, generation, inference, or critical
  evaluation.

## W3-002-CR1-EA1 authorization commit A — 2026-08-12

- **Task:** `W3-002-CR1-EA1-AUTH-A` (Week 3, P0), limited to the exact
  five-file authorization transition.
- **Candidate Revision 7:** `FROZEN / SENIOR SEMANTIC APPROVED / COMMITTED /
  PUSHED`; Candidate manifest, mapping, and Pass-B bytes remain unchanged.
- **EA1 Revision 12:** `SENIOR EXECUTION READINESS APPROVED / COMMITTED /
  PUSHED` as R2 `cec29477e3c75d132b54f787ba602a0a1b33f578`.
- **Authorization scope:**
  `EXACT_COMMITTED_CANDIDATE_AND_REVIEWED_EXECUTION_BYTES_ONLY`; Senior verdict
  `APPROVE_EXECUTION`.
- **Authorization:** `AUTHORIZED_FOR_PRIMARY_EXECUTION` with
  `evaluation_authorized=true`.
- **Lifecycle:** `critical_evaluated=false`, `model_verdict=NOT_ESTABLISHED`;
  Week 3 remains `BLOCKED / IN PROGRESS` and Week 4 remains `BLOCKED / NOT
  STARTED`.
- **Execution boundary:** primary execution must not start until Senior
  independently verifies the committed topology `HEAD=A` and `HEAD^=R2`. No
  model/encoder loading, retrieval, generation, inference, V0/V1/V2,
  gold/evaluator loading, or critical evaluation has occurred.

## Historical pre-CR1 handoff note

This handoff describes the earlier W3-001/W3-002 incident milestone and is
superseded for current operational status by `## Current status`,
`## Active objective`, `## Next 3 actions`, and the final SRD1 section.

Week 1 is complete and defensible. The exact semantic model/config above is frozen
for downstream PayResolve AI, with lexical retained as fallback. Git preflight on
2026-07-28 confirmed clean synchronized `main` at W1-004 commit `7c60110`.
W2-001 and W2-002 are committed and pushed. W2-003 ran the preregistered exact
dense R0 against the sole R1 soft-intent-boost variant on the frozen KB/mapping.
The locked evidence retained R0, reproduced exactly, and preserved zero status
leakage. Review correction separated safety diagnostics, persisted development
rankings, and removed routine verifier dependence on ignored artifacts without
changing accepted numerical results. Senior final verdict is `APPROVE_COMMIT`;
W2-003 is DONE / REVIEWED / ACCEPTED and the Week 2 P0 gate is PASSED. The
W3-001 implementation is DONE / REVIEWED / ACCEPTED, while the preregistered
gate-v1 result remains PARTIAL — UTILITY NOT DEMONSTRATED because it abstains on
all ten positive development cases. Senior verdict is `APPROVE_COMMIT — PARTIAL
BASELINE`; W3-001 overall is PARTIAL / REVIEWED / ACCEPTED. W3-001-CR1
implementation is COMPLETE. Its original frozen-mapping result remains FAILED and
is explicitly invalidated by incomplete relevance mapping; the Senior-approved
three-row adjudication passes safety and utility and is REVIEWED / ACCEPTED under
Senior verdict `APPROVE_COMMIT — QUALIFIED POST-HOC PASS`. This is not a pristine
holdout pass or final Week 3 safety pass. W3-002's numerical run is preserved,
but its critical set is INVALIDATED because the pre-evaluation mapping audit was
self-referential. The model/pipeline verdict is NOT ESTABLISHED. Week 3 P0 is
BLOCKED / IN PROGRESS and Week 4 is BLOCKED / NOT STARTED. Senior final verdict
for the incident evidence is `APPROVE_COMMIT — INTEGRITY INCIDENT EVIDENCE`;
W3-002 implementation and integrity analysis are DONE / REVIEWED / ACCEPTED.

## W3-002-CR1-EA1 readiness revision 13 — 2026-08-12

- Task: `W3-002-CR1-EA1-READINESS-R13`, remediation authoring only.
- Root cause: `EA1_RUNTIME_OFFLINE_ENCODER_BINDING_DEFECT`; Candidate Revision 7 is unchanged.
- Remediation: require `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `HF_HUB_OFFLINE=1`; pass `local_files_only=True`; hash-bind nine transitive runtime modules.
- Evidence: zero network attempts; `[1,384]` float32; norm 1.0; exact expected embedding SHA; snapshot 11/11; Candidate 23/23; payload 60/60 unchanged.
- Verification: focused 15/15, readiness 118/118, Rev10/11/12 30/30, Senior safety 3/3, full harness 655/655 PASS.
- Boundary: A12/E1 evidence remains byte-identical; reset is `NOT EXECUTED`; R13 is unauthorized and stopped on the environment gate. The pre-stop ZIP is non-deliverable. Week 3 is blocked/in progress; Week 4 is blocked/not started.

## W3-002-CR1-EA1 Revision-13 authorization/runtime closure binding — 2026-08-13

- Task: `W3-002-CR1-EA1-R13-BINDING-FIX-01` (Week 3, P0).
- Stable environment identity: canonicalization algorithm, 298-row package identity, required offline variables, exact CPython `3.13.3`, and normalized core-five version/METADATA/RECORD hashes are serialized canonically and bound by SHA-256 `17cd6dcf9d20d8b17d14369a10ba915f3047e27fffb7eec5771738442923fd97`.
- Runtime source closure: 18 production modules are reasoned, hashed, authorization-bound, and verified before model construction; empty package initializers are explicitly excluded.
- Fail-closed evidence: ENV-AUTH 01–07 and three source-tamper controls all reject before model/gold/evaluator calls. The final lineage-bound offline probe passed in 131.649789 seconds with zero network attempts.
- Verification: focused binding 12/12, ENV 12/12, R13 15/15, readiness 118/118, Rev10/11/12 30/30, safety 68/68, retrieval 56/56, and corrected full harness 679/679 in 299.132 seconds.
- Boundary: Candidate Revision 7 and E1 hashes remain unchanged; A12 remains historical; no reset, authorization, primary/evaluation, stage, commit, or push. Status is `R13_BINDING_FIX_READY_FOR_SENIOR_REVIEW`.

## W3-002-CR1-EA1 Revision-13 final authorization-date closure — 2026-08-13

- Task: `W3-002-CR1-EA1-R13-AUTH-DATE-CLOSURE-01` (Week 3, P0).
- Active R13 topology now deterministically derives the exact five future A13 paths from the reviewed config field `reports/week_03/daily/2026-08-13.md`; the 2026-08-12 path is stale/forbidden for active R13.
- Historical Revision-12 semantics remain covered by an isolated Revision-12 fixture where 2026-08-12 is valid and 2026-08-13 is future/unreviewed.
- All nine authorization/environment enforcement symbols remain defined in `src/payresolve_ai/evaluation/critical_v2_execution.py`, SHA-256 `983e99269fd006f2aa8dc3bf30e25558cda2d2c9a007218e2983ee1604af6a42`, within the 18-module closure, `READINESS_HASH_PATHS`, and the authorization candidate hash map. No new local enforcement module was introduced.
- Verification: auth-date/closure 9/9, binding 12/12, environment 12/12, R13 15/15, readiness 118/118, historical Rev12 5/5, Rev10 20/20, Rev11 5/5, safety 68/68, retrieval 56/56, and corrected full harness 688/688 in 225.925 seconds. The offline probe passed in 9.976939 seconds with zero network attempts.
- Boundary: Candidate Revision 7 and E1 evidence remain unchanged; A12 is historical only; reset remains `NOT EXECUTED`; `evaluation_authorized=false`, `critical_evaluated=false`, and `model_verdict=NOT_ESTABLISHED`. Status is `R13_FINAL_READY_FOR_SENIOR_REVIEW`.

## W3-002-CR1-EA1 Revision-13 review coverage correction — 2026-08-13

- `tests/test_retrieval_benchmark.py` is classified `R13_REGRESSION_COMPATIBILITY_TEST_CHANGE`: one test was renamed and strengthened to require frozen Week-2 provenance drift after the reviewed R13 local-only encoder change; no retrieval assertion/case was removed or weakened.
- The test SHA-256 `87bceeb60fd079bd380b095cd6a76ec714d871b0303a8215b5cd9bf7cb358fb7` is now in `READINESS_HASH_PATHS`, the pre-authorization Candidate execution-artifact map, bundle `task_files`, and detached inventory. It remains outside the 18-module runtime closure because it is not runtime code.
- A deterministic review-scope classifier and proposed-commit dry run now fail closed on unclassified dirty paths, omitted R13 paths, byte mismatches, protected E1 paths, review ZIPs, or user-owned paths.
- Verification: coverage 6/6, retrieval 56/56, all ordered suites pass, Senior safety 68/68, and final exact-byte corrected full harness 694/694 in 237.471 seconds. Final regenerated offline probe passed in 45.061138 seconds with zero network attempts and unchanged embedding SHA.
- Boundary: Candidate/E1/runtime/environment/auth-date semantics unchanged; reset `NOT EXECUTED`; no A13, primary/evaluation, stage, commit, or push. Status is `R13_REVIEW_COVERAGE_FIXED_READY_FOR_SENIOR_REVIEW`.

## W3-002-CR1-EA1 Revision-13 environment provenance remediation — 2026-08-12

- Task: `W3-002-CR1-EA1-R13-ENV-FP-FIX-01` (Week 3, P0).
- Classification: `ENV_DISCOVERY_CONTEXT_DRIFT / REMEDIATED`; no package installation drift and no package mutation.
- Canonical identity: PEP-503-normalized unique third-party rows excluding local `payresolve-ai`; 298 rows, SHA-256 `39c1c4a09994f3ea0b7691c796b39085f95fb985efa73207057fa5f7c187f25a` across C1/C2/C3/C4. Version conflicts fail closed; core-five metadata is explicitly bound.
- Verification: ENV 12/12, R13 15/15, readiness 118/118, REV10 20/20, REV11 5/5, REV12 5/5, safety 68/68, retrieval 56/56, and full repository harness 667/667 in 239.332 seconds. The final lineage-bound offline probe passed in 14.159185 seconds with zero network attempts and the locked embedding SHA.
- Lifecycle: Candidate Revision 7 remains unchanged/frozen/Senior approved; Revision 12 and A12 are historical only; R13 is ready for Senior readiness review. Primary is not run, `evaluation_authorized=false`, `critical_evaluated=false`, and `model_verdict=NOT_ESTABLISHED`. Week 3 remains blocked/in progress; Week 4 remains blocked/not started.

## W3-002-CR1-EA1 readiness revision 14 — 2026-08-13

- **Task:** `W3-002-CR1-EA1-R14-AUTH-VERIFIER-HARDENING` (Week 3, P0).
- **History:** R13 remains Senior readiness approved, committed, and pushed at `5d862e708f972b2fa73403fef390f2ac7b432435`, but is superseded for future execution after fail-closed A13 authoring exposed incomplete final-field validation and subset-only authorization topology validation. A13 was not created.
- **R14 remediation:** final authorization validation now binds the complete lifecycle identity, and authorization commits must change exactly the reviewed five paths. R14 regressions cover 11 field mutations and 11 negative topology cases plus the exact-five positive case.
- **Verification:** ordered matrix 88/88 in 23.562s; execution-readiness 118/118 in 68.984s; Senior safety 68/68 in 0.545s; retrieval 56/56 in 0.632s; corrected full harness 703/703 in 289.873s unittest / 293.8s process (5 unrelated skips). Offline probe passed in 17.945591s with zero network attempts and unchanged embedding SHA.
- **Lifecycle:** Candidate Revision 7 remains frozen/Senior approved. The reset archive and receipt remain exact; active runtime environment/state remain absent. R14 is `R14_READY_FOR_SENIOR_REVIEW`; A14 is not created, `evaluation_authorized=false`, `critical_evaluated=false`, and `model_verdict=NOT_ESTABLISHED`. PRIMARY is not authorized. Week 3 remains blocked/in progress and Week 4 blocked/not started.

## Proposed A14 authorization lifecycle — 2026-08-13

- Candidate Revision 7: frozen, Senior-approved, committed, and pushed.
- R13: historical and superseded for future execution; A13 was not created and authoring aborted fail-closed.
- R14: Senior readiness-approved, committed, and pushed at `c0afb7ba74cbcb778a5952399f1db628166df40d`.
- A14: `AUTHORIZED_FOR_PRIMARY_EXECUTION`; `evaluation_authorized=true`; `critical_evaluated=false`; `model_verdict=NOT_ESTABLISHED`.
- PRIMARY: NOT YET RUN. Week 3 remains blocked/in progress; Week 4 remains blocked/not started.
- Next: Senior verifies committed A14 topology before PRIMARY.

## W3-002-CR1-EA1 readiness revision 15 — 2026-08-13

- PRIMARY completed and was evaluated under historical R14/A14; its seven artifacts remain exact. Reproduction was not retried during R15 authoring.
- One canonical ordered six-input closure now drives evaluator evidence, transition recording, and validation at indexes 4 and 9; 12/12 transitions are exact.
- Fail-closed continuation requires exact R14/A14/state/runtime/PRIMARY fingerprints, proves frozen six-input provenance, writes one receipt, and separates historical from future runtime manifests.
- Isolated migration reaches pre-model Repro V0 with 0/0/0/0 runtime calls. Active state remains `PRIMARY_EVALUATED`, SHA-256 `6cab044610b566f4b7c6ecfbcafc5b49868891c167543ef950b20e29710416bd`.
- Status: `R15_READY_FOR_SENIOR_REVIEW`; A15 is not created and R15 is not authorized.

### R15 F1 continuation-authority correction — 2026-08-14

- Production migration obtains authority only through committed A15 verification and exact continuation lineage fields.
- One-shot CLI and fail-closed PREPARED/PASS transaction receipt are implemented; committed synthetic R15→A15 control passes with zero runtime calls.
- Active state/runtime and PRIMARY evidence remain exact. Status: `R15_CORRECTED_READY_FOR_SENIOR_REVIEW`.

### R15 F3 post-push committed-byte closure — 2026-08-14

- Initial R15 commit `5e89ec1ed2b7284ed5f263be674e3cb20e0facaf` is preserved and not rewritten.
- A complete 62-path audit found exactly four reviewed/hash-bound files absent from the committed tree, including the required `migrate-r15-continuation` CLI.
- The corrective readiness package remains Revision 15 and requires a new readiness commit on `5e89ec1`; future A15 must use that corrected commit as its direct parent.
- Candidate Revision 7, PRIMARY, active state/runtime, six-input closure, F1, F2, and 12/12 transitions remain unchanged. A15 remains unauthorized and reproduction was not retried.

### R15 F2 synthetic Git-config isolation correction — 2026-08-14

- Classification: `R15_SYNTHETIC_WORKTREE_SHARED_CONFIG_MUTATION`, reproduced only in a disposable repository for `user.name`, `user.email`, and `core.autocrlf`.
- Repository-local identity is restored to `dinhkhoi124` / `dinhkhoi1work@gmail.com`.
- Synthetic commits use command-local identity and config overrides; six phase guards preserve the common Git config exactly.
- Local `core.autocrlf=false` remains unchanged and requires Senior review before commit.
- Active state/runtime and PRIMARY remain exact; reproduction was not retried. Status: `R15_F2_CORRECTED_READY_FOR_SENIOR_REVIEW`.

### Proposed A15 continuation authorization — 2026-08-13

- Corrected R15-F3 readiness is Senior-approved, committed, and pushed at `a8dc336b73be6ec91b2280c56c048d348329cff5`; historical initial R15 commit `5e89ec1ed2b7284ed5f263be674e3cb20e0facaf` remains immutable.
- A15 is proposed with exact five-path topology and direct parent R15-F3. It authorizes only the one-shot `R14_PRIMARY_EVALUATED_TO_R15_CONTINUATION` migration and binds legacy A14 `1dd7e054f17f9aaf48dca87ba0e00611ca3f2094`, legacy R14 `c0afb7ba74cbcb778a5952399f1db628166df40d`, state `6cab044610b566f4b7c6ecfbcafc5b49868891c167543ef950b20e29710416bd`, and historical runtime `b036b8e337f809817dbbc6006e36d892c63480df2a919d9775279195c85bd22d`.
- Lifecycle: `evaluation_authorized=true`, `critical_evaluated=false`, `model_verdict=NOT_ESTABLISHED`. Historical PRIMARY is preserved and was not rerun.
- Real state is not migrated during authoring. Reproduction remains unauthorized until A15 is committed, production-verified, migration succeeds, and Senior separately permits the retry.
- Next: Senior reviews the proposed A15 bytes and synthetic committed-topology/migration evidence.


## A16 post-evaluation continuation authorization

- The real R15-F4-F1 comparator implementation correction is committed and pushed as `e6b49d4db4658251d68692aba812ad080ce5b3e1`.
- The real lifecycle state remains `REPRO_EVALUATED`; the frozen raw reproduction behavioral evidence remains `180/180` and substantively matches PRIMARY.
- A16 authorizes only the post-evaluation continuation required to bind the committed R15-F4-F1 readiness implementation before reproducibility verification.
- No model or evaluator rerun is authorized. Real `verify-reproducibility` has not run, finalization has not run, and the model verdict remains `NOT_ESTABLISHED`.
- This authoring package does not claim `REPRO_VERIFIED`, `FINALIZED`, Week 3 P0 completion, or model approval.


### W3-002-CR1-EA1 A17 post-verify continuation authorization — 2026-08-16

- R15-F5-F1 is published as `328757ffd768ce9603b3ee596f74505afa1b4a4c`.
- At A17 authoring time, the real lifecycle was `REPRO_VERIFIED` with history length 11; reproducibility was provenance-valid and behaviorally identical for 180/180 rows.
- A17 authorizes only `R15_F5_POSTVERIFY_CONTINUATION` to bind the corrected finalization implementation to the existing verified evidence.
- At that authoring milestone, real post-verify continuation, finalization, and `verify-results` had not run and the final summary was absent; those steps subsequently completed under separate Senior authorizations.
- Before finalization, `critical_evaluated=false` and `model_verdict=NOT_ESTABLISHED`; A17 alone does not establish model approval or complete the Week 3 P0 gate.
- Candidate Revision 7, PRIMARY, reproduction, comparison, and historical lifecycle evidence remain immutable.

## SRD1 Senior result decision — 2026-08-16

- **Technical integrity:** `DONE / FINALIZED / VERIFY_RESULTS_PASS`. The finalized
  execution state remains `FINALIZED` with history length 12, and PRIMARY versus
  REPRO remains behaviorally identical for 180/180 rows.
- **Model/pipeline result:** `NOT_APPROVED_FOR_PRODUCT_INTEGRATION /
  REMEDIATION_REQUIRED`; selected variant is `NONE`.
- **Variant disposition:** V0 is rejected for low utility and over-abstention;
  V1 is rejected because the soft intent boost produces no end-to-end gain over
  V0; V2 is rejected for unsafe prohibited-request compliance and abstain failure.
- **Decision basis:** all variants fail all 15 Safe Corrective cases; V0/V1
  incorrectly abstain on 45/55 answerable cases; V2 fails all five true-abstain
  cases and contains five evaluator-classified unsafe outcomes. This is a
  categorical safety/product-contract decision, not a newly invented numeric
  threshold failure.
- **Grounding/reproducibility:** citation correctness is 1.0, unsupported-claim
  rate is 0.0, and Draft/Expired/Future effective usage is 0.0 for every
  variant. The weaknesses are stable and reproducible; grounding integrity is
  strong. Do not infer that the Banking77 classifier alone is the root cause.
- **Gates:** W3 evaluation work is `COMPLETE`; the W3 P0 product gate is
  `NOT_CLOSED_REMEDIATION_REQUIRED`; W4 real AI integration remains `BLOCKED`.
- **Locked-eval policy:** Candidate Rev7 and its PRIMARY/REPRO results remain
  immutable. Do not tune against Rev7 or rerun it as a fresh holdout. Future
  remediation must use non-locked development evidence and a separately
  authorized independent evaluation before any new product-approval claim.
- **Next task:** `W3-003 — Grounded RAG Behavior Remediation`, planning only.

## W3-003-EV1-C2 Fix1 portable runtime readiness — 2026-08-18

- C1 remains immutable at `fbac31554cee13de22fb58de0c962f0f8b7b3b2c` with parent R `5f7216fd64ad6a7518480318ff2fe4862a06abc3`.
- C2 binds Git-canonical runtime sources separately from 14 external immutable runtime assets.
- The external ZIP receipt is committed metadata: authorization A must match both SHA-256 and byte size, plus the runtime-asset and C2 manifest hashes.
- Provisioning validates the receipt and exact inventory, then materializes 11 encoder snapshot files as ordinary copies; no symlink privilege is required.
- Load-only readiness passed for the exact MiniLM revision on CPU with `local_files_only=true`, `trust_remote_code=false`, dimension 384, and zero network/encode/EV1-input accesses.
- Authorization, EV1 inference, PRIMARY, evaluation, reproduction, and finalization remain absent; W4 remains blocked pending Senior review and publication.
