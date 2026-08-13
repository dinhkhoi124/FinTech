# W3-002-CR1-EA1 — Readiness Revision 9

## Hypothesis

The rejected EA1 architecture can be safely rebound to frozen candidate revision
7 without candidate mutation, while closing the six COV1 evaluator gaps and
preserving fail-closed authorization, runtime/gold isolation, write-once outputs,
and exact provenance.

## Result

PASS for readiness revision-9 packaging; evaluation remains unauthorized.

- Candidate immutable-byte verification: 23/23 artifacts.
- Runtime payload isolation: 60 payloads, zero forbidden evaluator/gold fields.
- Obligation rules: 55 answerable queries, 148 required obligations, 219 exact
  atomic sentence requirements, and 13 semantic rejects.
- Canonical cover equivalence: candidate 92, evaluator 92, missing 0,
  same-cardinality extra 0, smaller-than-candidate 0.
- Inclusion-minimal diagnostic total: 96, comprising 92 canonical covers and four
  valid larger noncanonical covers.
- Independent brute-force reference: 55/55 query agreement, 92/92 canonical,
  four larger diagnostics.
- COV1 safety: 6/6 PASS.
- Exact Senior revision-9 safety regression set: 38/38 PASS, retaining all 22
  revision-8 cases and adding 16 ID02/ID03/ID04 target-order cases.
- Explicit target contract: 15 classified SAFE_CORRECTIVE queries, eight
  disclosure-capable queries, and 11 canonical disclosure targets.
- Disclosure fixture-quality gate: 176 fixtures, zero malformed constructions.
- Full target-specific safety matrix: 256 cases, zero false positives, zero false
  negatives.
- Full observed mutation campaign: 30 rows, zero unexpected passes.
- Final self-adversarial review: eight concrete categories, 8/8 PASS.
- Focused EA1 tests: 118/118 PASS.
- Related candidate/Option-A/feasibility/W3 safety tests: 210/210 PASS.
- Isolated exact-byte application suite: 617/617 PASS with eight reported
  context/runtime-asset skips. Two review-bundle-context modules were excluded.

The final isolated harness copies exact current bytes for clean tracked files,
uses HEAD object bytes for unrelated modified files, overlays only the 56 EA1
task paths, and supplies the immutable ignored Banking77 raw snapshot. This is
required because the frozen repository intentionally contains both LF-bound
and checked-out CRLF-bound artifact hashes.

## Definition correction

The initial implementation incorrectly compared the candidate's frozen
minimum-cardinality covers (92) with all evaluator inclusion-minimal covers (96).
Senior clarified that only minimum-cardinality covers are canonical. The four
larger inclusion-minimal alternatives are valid and remain preserved as
`VALID_NONCANONICAL_LARGER_COVER`; no obligation alternative or candidate byte
was removed to force equality.

## Safety and provenance hardening

Disclosure parsing distinguishes target mentions, non-availability,
non-support, non-approval, safe negation, and actual disclosure with deterministic
longest-pattern precedence. A later affirmative action remains unsafe even after
an earlier negation. Runtime assets, payloads, environment expectation,
authorization candidate, future command plan, raw execution IDs, and state
machine all bind revision 7. The classified stale-binding audit reports zero
forbidden active revision-6 bindings.

## Boundary

No model, encoder, retrieval, generation, inference, or critical evaluation ran.
No staging, commit, or push occurred. Current lifecycle is
`FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_AUTHORIZATION_REVIEW` with
`evaluation_authorized=false`, `critical_evaluated=false`, and
`model_verdict=NOT_ESTABLISHED`.

## Revision-7 readiness history

Senior rejected readiness revision 7 for incomplete negative-predicate and
payload-ordering semantics, summary-only mutation/self-adversarial evidence, and
the stale authorization daily path. Its external ZIP remains preserved at
SHA-256 `dc72ab6d074c3dd3eb3391586ec783c8b287abbb44114e872e048c4cf5c9757c`.
Candidate Revision 7 was not rejected or changed.

## Revision-8 readiness history

Senior rejected readiness revision 8 for incomplete disclosure-target coverage
on ID02, ID03, and ID04 and for constructing adversarial fixtures from
verb-bearing sentence templates instead of canonical bare targets. The rejected
ZIP remains preserved at SHA-256
`3291975173dff7e8afb0da4ab368d32e8f1913020bc9951f5e56b3b8686fe218`.
Revision 9 preserves every verified cover, obligation, authorization, and
provenance invariant from revision 8 while correcting only those safety-harness
defects. Candidate Revision 7 was not rejected or modified.

## Readiness Revision 10 — three-finding closure

### Context and root causes

Senior review identified three remaining readiness gaps. Amendment 1 adjudicated
the original F1 premise as invalid because production has no runtime
STANDARD/SAFE_CORRECTIVE branch. F2 lacked a bounded literal/evidence
defense-in-depth layer. F3 duplicated incomplete raw provenance checks across
lifecycle boundaries.

### Narrow solution

- `F1_POST_FREEZE_SUBTYPE_SEPARATION`: raw subtype is null-only and non-null
  injection fails with `RAW_PRE_FREEZE_SUBTYPE_FORBIDDEN`; subtype classification
  remains evaluator-only after freeze.
- `F2_NARROW_DISCLOSURE_GUARD`: derive the exact eight-query/11-target inventory
  from Revision-9 evidence. Because no authoritative literal values are
  enumerated, record that fact for all targets and retain the parser as fallback;
  combine parser and guard using fail-closed OR.
- `F3_RAW_EXECUTION_PROVENANCE`: reuse one authoritative validator at raw
  persistence, freeze, and pre-gold boundaries.

### Verification and limitations

Focused tests pass 20/20; the historical readiness suite remains 118/118 PASS;
combined focused tests pass 138/138; related suites pass 210/210; and the
isolated exact-byte application suite passes 637/637 with eight explicit skips.
Active readiness and detached-bundle verification pass. F2 does not claim
absence of arbitrary or fabricated secrets and does not implement generalized
English/NLI/embedding detection. Hybrid/structured disclosure hardening is
deferred and is not a Week-3 P0 blocker. Failed harness/test attempts remain
recorded.

No Candidate Revision 7 bytes changed. No runtime policy router, query-ID subtype
hardcode, pre-freeze Candidate mapping load, public API, inference, or critical
evaluation was introduced. EA1 Revision 10 was submitted for Senior review and
did not authorize evaluation.

## Readiness Revision 11 — F3 batch membership closure

Senior review found that Revision 10 validated rows independently but allowed 60
copies of one otherwise valid frozen query to reach persistence. Revision 10 is
therefore `SENIOR_REVIEWED / F3_BATCH_MEMBERSHIP_DEFECT_FOUND`, reason
`RAW_BATCH_EXACT_MEMBERSHIP_NOT_ENFORCED_PRE_PERSISTENCE`.

Revision 11 adds one authoritative `validate_raw_run_binding` invariant:
`row_count=60`, `unique_query_id_count=60`, and exact set equality with frozen
runtime membership. Only after that passes does it reuse
`validate_raw_execution_binding` for every row. The guard is called at
persistence, freeze, and pre-gold boundaries. F3-J…N pass 5/5; the 60-duplicate
Senior reproducer and 59+duplicate fixture are rejected with zero persistence or
state side effects, exact 60 unique passes, and both freeze/pre-gold duplicate
tampering are blocked. F1/F2 remain closed without semantic re-review.

No inference or critical evaluation ran. Revision 11 is
`FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_AUTHORIZATION_REVIEW` with
`evaluation_authorized=false`, `critical_evaluated=false`, and
`model_verdict=NOT_ESTABLISHED`.

## Revision 12 — authorization daily-path rollover

The committed Revision-11 readiness package remains Senior-approved at
`c7bc68bbef51684f6ff4ab7a672ca78af4cbbadd` for all F1/F2/F3 semantics. A
narrow calendar-topology conflict was reproduced: the production contract and
validator allowed only `daily/2026-08-11.md` and rejected the now-reviewed
`daily/2026-08-12.md` path.

Revision 12 changes only the active readiness revision, exact authorization
allowlist, its validator/tests, and mechanically dependent hashes. AUTH-DATE-01
through AUTH-DATE-05 pass. No evaluator, disclosure, provenance, batch,
Candidate, metric, model, retrieval, generation, inference, or evaluation
semantics changed. The status is `FROZEN_READINESS_PACKAGE /
AWAITING_SENIOR_REVIEW`; authorization remains false.

## Revision 13 — offline encoder and runtime-source provenance

### Canonical environment fingerprint remediation

Hypothesis: raw distribution drift is caused by discovery context, not package
installation changes. Package installation state remained fixed while only
`sys.path`/`PYTHONPATH` discovery contexts varied. C1/C2/C3/C4 raw counts were
300/301/302/301, while all canonical third-party inventories remained 298 rows
at `39c1c4a09994f3ea0b7691c796b39085f95fb985efa73207057fa5f7c187f25a`.
Synthetic conflicting versions were rejected as
`CONFLICTING_DISTRIBUTION_VERSIONS_REJECTED`, closing the provenance stop without
package mutation.

Two E1 failures established a runtime-readiness defect before raw persistence:
120.817 seconds/exit 124, then 32.210 seconds/exit 1 with a blocked Hugging Face
HEAD request. The A+B remediation binds `HF_HUB_OFFLINE=1` and
`local_files_only=True` without changing model semantics and hash-binds the
nine-module production chain. The diagnostic observed zero network attempts
and reproduced the expected embedding SHA in 14.749808 seconds. Assets remain
11/11; payloads remain identical 60/60; A12 is rejected; reset was not executed.
All ordered suites pass, including the 655/655 full harness.

## R13 authorization/runtime binding remediation — 2026-08-13

- Hypothesis: binding a deterministic stable environment identity and the complete local source closure will make authorization and runtime equivalent at the pre-model boundary.
- Stable identity result: 298 canonical third-party rows; package SHA-256 `39c1c4a09994f3ea0b7691c796b39085f95fb985efa73207057fa5f7c187f25a`; environment identity SHA-256 `17cd6dcf9d20d8b17d14369a10ba915f3047e27fffb7eec5771738442923fd97`.
- Closure result: 18/18 modules are reasoned and authorization-bound; empty package initializers are reviewed exclusions.
- Adversarial result: seven environment identity mutations and three source mutations all stop before model/gold/evaluator calls; detached verifier mutations are also rejected.
- Runtime result: final offline encoder probe passed in 131.649789 seconds, zero network attempts, expected embedding identity preserved.
- Test result: all focused/ordered suites pass and corrected full harness is 679/679 in 299.132 seconds. No primary inference or evaluation ran.

## R13 final authorization-date topology closure — 2026-08-13

- Controlled variable: only active authorization daily-path topology and its regression/verifier coverage changed; Candidate, environment identity, runtime semantics, payload, assets, and 18-module closure membership were held fixed.
- Active result: exact-five allowlist binds `daily/2026-08-13.md`; 2026-08-12 is rejected as stale, 2026-08-11 as older, 2026-08-14 as unreviewed, and missing/dual/source-path mutations are rejected.
- Historical result: Revision-12 2026-08-12 semantics pass using an explicit Revision-12 config fixture.
- Enforcement result: nine trust-boundary symbols remain in the root execution module and are source/hash/authorization bound; root source SHA-256 is `983e99269fd006f2aa8dc3bf30e25558cda2d2c9a007218e2983ee1604af6a42`.
- Runtime result: synthetic offline probe passed in 9.976939 seconds, zero network attempts, unchanged embedding SHA; no Candidate query or evaluator was loaded.
- Test result: all ordered suites pass; corrected full harness is 688/688 in 225.925 seconds.

## R13 review-package coverage correction — 2026-08-13

- Diff classification: `R13_REGRESSION_COMPATIBILITY_TEST_CHANGE`; HEAD SHA `bb1b6d2051fa3dce9d7afe8624c133b17761bcbbda41a5a08a5eb228016ee984`, working SHA `87bceeb60fd079bd380b095cd6a76ec714d871b0303a8215b5cd9bf7cb358fb7`.
- The changed test replaces a stale PASS expectation with a stricter `implementation hash mismatch` expectation while preserving mocks proving no cache/model/encoder load. No production or R0/R1 semantics changed.
- The test is now readiness/authorization hash-bound and bundled. Review-scope omission and unreviewed-task-owned-path controls fail closed.
- Final regenerated offline probe: 45.061138 seconds, zero network attempts, unchanged embedding identity. Final exact-byte full harness: 694/694 in 237.471 seconds process time.
