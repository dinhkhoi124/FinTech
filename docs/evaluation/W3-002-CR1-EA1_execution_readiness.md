# W3-002-CR1-EA1 Execution Readiness

Active readiness revision: **14**. Candidate revision: **7**.

## Revision 14 authorization-verifier hardening

R13 remains historically Senior-approved, committed, and pushed at
`5d862e708f972b2fa73403fef390f2ac7b432435`. During isolated A13 authoring,
two fail-closed gaps were proven before any package was created: incomplete
final-authorization lifecycle-field validation and subset acceptance for the
five-path authorization topology. Revision 14 supersedes R13 only for future
execution readiness.

R14 requires exact equality for all final authorization fields and requires the
authorization commit diff to equal—rather than be a subset of—the exact five
reviewed paths. The authorization date remains `2026-08-13`. Candidate Revision
7 and the R13-reviewed environment identity remain unchanged. The real R14
candidate is non-authorized; A14 and PRIMARY remain forbidden pending separate
Senior review and commit/topology verification.

## Purpose

This contract prepares deterministic, fail-closed execution infrastructure for
the frozen W3-002-CR1 candidate revision 7. It does not authorize model loading,
retrieval, generation, inference, gold loading before raw freeze, or critical
evaluation.

## Frozen candidate binding

- Candidate revision: 7
- Candidate commit: `18a1840f39fef8f07337ff357f7991292389bae9`
- Candidate manifest SHA-256:
  `f912798ae5c02c774702ae97bee8b2b4f6c6ab12b6534e1b2a3817a969b905ef`
- Mapping SHA-256:
  `cc9e82adbb97fd8054e58d3d6548ca03b15046bb37eca53ef9aa529dc4ec12f1`
- Distribution: 40 STANDARD / 15 SAFE_CORRECTIVE / 5 ABSTAIN_ESCALATE

## Readiness gates

- Candidate bytes and 23 manifest artifacts must verify exactly.
- Runtime payloads contain only query ID, model-input text, and its SHA-256.
- Runtime assets and encoder snapshot are content-hash bound before model load.
- Execution requires a separate committed Senior authorization record with
  topology `parent(A)=R`.
- Raw outputs are write-once and must freeze before any gold/evaluator load.
- State transitions and their direct input/output hashes are validated exactly.
- Canonical evaluator covers are minimum-cardinality complete covers. They must
  equal the frozen candidate set across all 55 answerable queries (92 covers).
- Larger inclusion-minimal covers remain noncanonical diagnostic evidence.
- Safety rules must pass all six COV1 regressions and the target-specific
  adversarial matrix with zero false positives and zero false negatives.
- Readiness revision 9 requires explicit target classification for all 15
  SAFE_CORRECTIVE queries, 11 canonical disclosure targets across eight
  disclosure-capable queries, 38 exact Senior safety rows, a pre-evaluator
  fixture-quality gate, complete per-target grammar coverage, a full
  per-mutation campaign, and eight concrete self-adversarial categories.
- Authorization commit A may update only the authorization record, canonical
  lifecycle files, week summary, and `daily/2026-08-11.md`; the stale
  `daily/2026-08-10.md` path is forbidden.
- Active generated readiness/runtime provenance must bind revision 7; historical
  revision-6 references and detector fixtures are classified separately.

## Current state

`FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_AUTHORIZATION_REVIEW`.
`evaluation_authorized=false`, `critical_evaluated=false`, and
`model_verdict=NOT_ESTABLISHED`. Candidate revisions 8 and 9 do not exist.

Readiness revision 7 is rejected review history, bound to external ZIP SHA-256
`dc72ab6d074c3dd3eb3391586ec783c8b287abbb44114e872e048c4cf5c9757c`.
This does not reject or modify Candidate Revision 7.

Readiness revision 8 is also rejected review history:
`REJECTED_BY_SENIOR / DISCLOSURE_TARGET_COVERAGE_INCOMPLETE /
ADVERSARIAL_FIXTURE_TARGET_CONSTRUCTION_INVALID`. Its external review ZIP is
bound at SHA-256
`3291975173dff7e8afb0da4ab368d32e8f1913020bc9951f5e56b3b8686fe218`.
Revision 9 corrects ID02/ID03/ID04 disclosure ordering and constructs every
adversarial disclosure fixture from its canonical bare target phrase.

## Senior-reviewed predecessor: readiness revision 10

Revision 10 closes only F1 post-freeze subtype separation, F2 narrow registered
disclosure guard, and F3 strict raw provenance. Raw subtype is null-only;
STANDARD/SAFE_CORRECTIVE is derived only after freeze. The literal registry is
limited to the current eight disclosure-capable queries and 11 canonical targets
and contains zero invented literals. One provenance validator is enforced before
persistence, freeze, and evaluator/gold load.

Senior review changed its status to `SENIOR_REVIEWED /
F3_BATCH_MEMBERSHIP_DEFECT_FOUND` because exact run-level membership was not
enforced before persistence.

## Active closure: readiness revision 11

Revision 11 closes only that F3 defect. `validate_raw_run_binding` requires 60
rows, 60 unique query IDs, and exact equality with the frozen runtime-payload
query set before delegating to the settled per-row validator. The same batch
guard is used before persistence, before freeze, and before evaluator/gold load.
F1 and F2 remain closed and regression-only.

Status is `FROZEN_READINESS_PACKAGE /
AWAITING_SENIOR_AUTHORIZATION_REVIEW`. `evaluation_authorized=false`,
`critical_evaluated=false`, and `model_verdict=NOT_ESTABLISHED`.

## Readiness Revision 12 — authorization date topology only

Revision 11 was Senior-approved, committed, and pushed at
`c7bc68bbef51684f6ff4ab7a672ca78af4cbbadd`. It remains accepted for F1, F2,
F3 row provenance, and F3 batch membership provenance. Revision 12 supersedes
it only because authorization commit A is now planned for 2026-08-12 while the
committed topology allowed only the prior daily report.

The authoritative allowlist now contains exactly the authorization record,
`PROJECT_STATE.md`, `TASKS.md`, the Week-3 summary, and
`reports/week_03/daily/2026-08-12.md`. The 2026-08-11, 2026-08-10,
2026-08-13, arbitrary daily, Candidate, and execution/source paths are rejected.
The amendment is explicit and contains no wall-clock routing.

Revision 12 is `FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_REVIEW` with reason
`AUTHORIZATION_DAILY_REPORT_DATE_ROLLOVER`. `evaluation_authorized=false`,
`critical_evaluated=false`, and `model_verdict=NOT_ESTABLISHED`; no
authorization record A or evaluation output exists.

## Readiness Revision 13 — offline runtime remediation

Real E1 attempts under A12 stopped before raw persistence: 120.817-second
watchdog timeout, then a 32.210-second failure caused by a Hugging Face HEAD
attempt (`WinError 10013`). Revision 13 requires exactly `OMP_NUM_THREADS=1`,
`MKL_NUM_THREADS=1`, and `HF_HUB_OFFLINE=1`; the critical retrieval path passes
`local_files_only=True`. All nine transitive runtime modules are hash-bound.

The bounded diagnostic observed zero network attempts and produced `[1,384]`
float32, norm 1.0, SHA-256
`83483507be7e9c48ca8caff139e15dc3e1f88509addd55793b7fc96e95f87f8e`.
A12 cannot authorize R13. The E1 pair remains preserved; reset is not executed.

### Revision-13 canonical environment provenance correction

Raw `importlib.metadata.distributions()` multiplicity is diagnostic only because
`.pth`, editable metadata, and repeated source roots alter it. Readiness and
future runtime now share one authoritative identity: PEP-503-normalized unique
third-party `name==version` rows, excluding local `payresolve-ai` whose sources
remain explicitly hash-bound. Multiple versions of one normalized name fail
closed. C1/C2/C3/C4 produced raw counts 300/301/302/301 but the same 298-row
fingerprint `39c1c4a09994f3ea0b7691c796b39085f95fb985efa73207057fa5f7c187f25a`.
Core-five ML metadata is separately bound. R13 is ready for Senior readiness
review, remains unauthorized, and does not authorize primary execution.

## Revision-13 binding closure — 2026-08-13

`W3-002-CR1-EA1-R13-BINDING-FIX-01` closes the gap between reviewed environment provenance and execution authorization. A deterministic canonical environment contract binds the 298-package identity, required offline variables, CPython 3.13.3, and core-five version/METADATA/RECORD hashes under identity SHA-256 `17cd6dcf9d20d8b17d14369a10ba915f3047e27fffb7eec5771738442923fd97`. The authorization candidate and readiness hash map bind that contract, and runtime checks the live identity before model construction.

The local production source closure contains 18 modules, including `generation/verification.py` and `data/banking77.py`; all are reasoned, hashed, and authorization-bound. ENV-AUTH 01–07, three source-tamper controls, and two detached bundle mutations fail closed. The offline probe passed in 131.649789 seconds with zero network attempts, and the corrected full harness passed 679/679 in 299.132 seconds. R13 remains unauthorized and primary was not run.

## Revision-13 final authorization-date closure — 2026-08-13

Active R13 now carries an explicit reviewed daily-report field and validates an exact five-path future-A13 allowlist containing `reports/week_03/daily/2026-08-13.md`. The validator does not use wall-clock time or filesystem discovery. Active use of 2026-08-12, older dates, 2026-08-14, both daily paths, a missing reviewed daily path, or any source/Candidate path fails closed. Revision-12 uses a constructed historical fixture so its original 2026-08-12 behavior remains regression-tested without constraining active R13.

The nine environment/authorization enforcement functions remain in `src/payresolve_ai/evaluation/critical_v2_execution.py`; the closure row now names package canonicalization, stable environment identity, authorization payload enforcement, runtime equality, daily-path topology, and state-machine entry explicitly. The file is in the 18-module runtime closure, `READINESS_HASH_PATHS`, and authorization hash map. No module was added. All ordered suites and 688/688 corrected full-harness tests pass. R13 remains pre-authorization and no primary inference ran.

## Revision-13 review coverage correction — 2026-08-13

The commit dry run discovered that `tests/test_retrieval_benchmark.py` contained an R13 regression-compatibility change but was absent from the review package and readiness hash surface. Exact review confirmed one strengthened test only: the frozen Week-2 verifier must now expose the intentional post-Week-2 `benchmark.py` provenance drift without loading cache/model/encoder. No R0/R1 behavior, assertion, or regression case was weakened or removed.

The test is now authorization/readiness hash-bound and included in bundle `task_files` and inventory, while remaining outside the 18-module runtime closure. A deterministic review-scope audit classifies every dirty path, requires byte equality for every proposed R13 commit path, and fails closed for omissions or unclassified paths. Focused coverage passes 6/6, retrieval 56/56, and the corrected full harness 694/694.
