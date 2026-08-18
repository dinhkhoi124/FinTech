# Task Board

Use stable task IDs. Do not delete completed tasks; preserve history.

Status: `TODO | IN_PROGRESS | BLOCKED | DONE | DEFERRED`
Priority: `P0 | P1 | P2`

| ID | Week | Priority | Task | Acceptance evidence | Status |
|---|---:|---|---|---|---|
| BOOT-001 | 0 | P0 | Integrate minimal project/reporting structure and automation | Required files exist; reporting tests and validation pass | DONE |
| BOOT-002 | 0 | P0 | Audit repo, Git/public safety, and developer commands | Audit evidence recorded; commands executed in current environment | DONE |
| BOOT-003 | 0 | P0 | Final Phase 0 consistency, scope-lock, environment, and safety review | Source-of-truth reconciled; Python 3.11 gate, tests, validator, and Git audit pass | DONE |
| DOC-001 | — | P0 | Generate reader-friendly views of authoritative MASTER_PRD | `tai_lieu/` index + section-completeness check; master remains authoritative and unchanged | DONE |
| DOC-002 | 3 | P0 | Prepare mentor sprint-report draft from official CSV template | Markdown mirrors all requested CSV fields and uses verified project evidence only | DONE |
| DOC-003 | 3 | P0 | Populate mentor sprint workbook from the approved Markdown draft | Four-sheet XLSX preserves template structure, renders legibly, reopens with intact Unicode, and passes content/error checks | DONE |
| W1-001 | 1 | P0 | Audit Banking77 and lock split | Audit artifact + deterministic split/config | DONE |
| W1-002 | 1 | P0 | Lexical baseline | Metrics + config + reproducible command | DONE |
| W1-003 | 1 | P0 | Semantic/model baseline | Metrics + config + reproducible command | DONE |
| W1-004 | 1 | P0 | Evaluation, confusion/error analysis, and Week 1 gate | Metrics/confusions/examples/gate decision + summary | DONE |
| W2-001 | 2 | P0 | Synthetic KB specification/generation/validation | Versioned KB + validation evidence | DONE |
| W2-002 | 2 | P0 | Gold evidence mapping | Locked mapping/eval data | DONE |
| W2-003 | 2 | P0 | R0 vs R1 retrieval benchmark | Controlled metrics + error analysis | DONE |
| W3-001 | 3 | P0 | Grounded pipeline + evidence gate | Implementation accepted; gate-v1 utility not demonstrated | DONE |
| W3-001-CR1 | 3 | P0 | Evidence Gate Utility Recovery v2 | Original FAILED history + exhaustive mapping audit + qualified post-hoc PASS evidence | DONE / REVIEWED / ACCEPTED |
| W3-002 | 3 | P0 | Critical safety evaluation + integrity incident | Execution preserved as diagnostic evidence; critical set invalidated; model verdict not established | DONE / REVIEWED / ACCEPTED |
| W3-002-CR1 | 3 | P0 | Pristine Critical Evaluation Recovery | Technical lifecycle finalized and verify-results PASS; Senior product verdict requires remediation and approves no variant | DONE / PRODUCT GATE NOT CLOSED |
| W3-003 | 3 | P0 | Grounded RAG Behavior Remediation | V3 remediation selected and frozen; independent product-gate evaluation must pass before W4 opens | IN_PROGRESS / PRODUCT GATE PENDING |
| W3-003-EV1 | 3 | P0 | Independent 60-case product-gate package | Blind 30/15/15 candidate frozen before inference; Senior semantic membership accepted | DONE / SUPERSEDED PRE-INFERENCE BY R2 |
| W3-003-EV1-R2 | 3 | P0 | Execution topology and evaluator-integrity closure | `A^=C` authorization topology, per-claim metrics, 45-case obligation rules, rendered safety, reproduction freeze, dummy-only tests | DONE / AWAITING SENIOR REVIEW |
| W3-003-EV1-R3 | 3 | P0 | Atomic claim reachability and committed authorization closure | 61 obligations preserved; 45/45 fit frozen claim budgets; immutable 19-path package published as C1 | DONE / COMMITTED / PUSHED |
| W3-003-EV1-C2 | 3 | P0 | Portable runtime-binding correction | SHA+bytes-bound runtime ZIP; copy-materialized encoder snapshot; offline load-only proof | DONE / AWAITING SENIOR REVIEW |
| W4-001 | 4 | P0 | Minimal service/logging/versioning/tests | Runnable API + evidence | TODO |
| W4-002 | 4 | P0 | Incident exercise | Postmortem + regression test | TODO |
| W5-001 | 5 | P0 | Freeze and final evaluation | Locked final evidence | TODO |
| W5-002 | 5 | P0 | One deep change request | Design/trade-off note | TODO |
| W5-003 | 5 | P0 | Final report/demo | Mentor-ready artifacts | TODO |

## Week 1 executable task contracts

All four tasks are P0 and were completed under the frozen Week 1 protocol. The
historical contracts below are retained for audit; do not reopen them for tuning.

### W1-001 — Banking77 data audit and deterministic locked split

- **Objective:** establish a reviewed, versioned full-77-intent data contract and
  deterministic train/validation/locked-test split before modeling.
- **Inputs:** authoritative Banking77 public source/version and license reference;
  upstream labels/examples; `docs/MASTER_PRD.md` leakage and split rules.
- **Outputs:** acquisition/version/checksum manifest; class-distribution and data
  quality audit; deterministic split definition with seed and immutable sample IDs
  or hashes; preprocessing/label contract; runnable CLI/config; locked-test usage
  warning.
- **Acceptance criteria:** all 77 labels are present and mapped deterministically;
  split membership is disjoint and repeatable from recorded inputs/config; exact
  duplicates and basic leakage risks are quantified; short/ambiguous examples and
  near-duplicate method/limitations are documented; no test example is used for
  tuning; important label/preprocessing/split invariants have tests.
- **Test/evidence:** data manifest/checksums, audit tables, split counts/hashes,
  exact reproduction command, and passing tests under `tests/`; no benchmark
  metric is required for this task.
- **Report updates:** today's `reports/week_01/daily/`; a W1-001 data-audit/design
  note under `reports/week_01/experiments/`; safe tables/manifests under
  `reports/week_01/results/`; `PROJECT_STATE.md`, this board, and the Week 1
  summary only for verified milestone changes.

### W1-002 — Lexical baseline

- **Objective:** produce the required simple lexical reference (TF-IDF + Logistic
  Regression or a justified equivalent) on the frozen W1-001 contract.
- **Inputs:** W1-001 train/validation split and label/preprocessing contract;
  versioned lexical config and seed; locked test reserved for the controlled
  evaluation protocol.
- **Outputs:** reproducible train/evaluate CLI, fitted local artifact/version
  metadata, raw validation/final-evaluation outputs at approved checkpoints, and
  accuracy, macro-F1, and per-class metrics artifacts.
- **Acceptance criteria:** deterministic rerun from config; no hidden notebook-only
  step; hyperparameters selected without locked-test tuning; predictions align
  exactly with sample IDs/label mapping; metrics are generated by code and trace
  to config/data/model versions.
- **Test/evidence:** passing preprocessing/feature-label alignment tests; exact
  commands; machine-readable predictions/metrics plus mentor-facing table; actual
  failures and runtime limitations retained in evidence.
- **Report updates:** today's daily report; a controlled lexical experiment note;
  relevant `results/`; `PROJECT_STATE.md`, this board, and progressive Week 1
  summary with evidence links (not copied unsupported numbers).

Completion record (2026-07-23): selected `word_unigram` from exactly two controlled
validation candidates with accuracy 0.865672 and macro-F1 0.862649. The CLI,
config, pinned dependencies, per-class metrics, aligned predictions, confusions,
portable local fitted parameters, manifest hashes, and passing tests are retained.
`test_evaluated=false`; official test remains reserved for W1-004.

### W1-003 — Semantic/model-based baseline

- **Objective:** run exactly one justified semantic/model-based approach under the
  same split and evaluation contract to test H1 against W1-002.
- **Inputs:** identical W1-001 split/labels and evaluation code; one reviewed model
  identifier/revision and versioned config; fixed comparison variables documented
  before execution.
- **Outputs:** reproducible train/inference/evaluate CLI; model/version metadata;
  predictions; accuracy, macro-F1, per-class metrics; resource/runtime notes; one
  controlled comparison against W1-002.
- **Acceptance criteria:** only the model representation/approach changes unless a
  deviation is explicitly justified; same locked sample IDs and metric code are
  used; seed/model revision/dependencies are captured; locked test is not used for
  tuning; no third model is started.
- **Test/evidence:** config and exact commands; sample/prediction alignment tests;
  raw metrics/predictions and comparison table; recorded runtime/environment and
  any unavailable model/download limitation.
- **Report updates:** today's daily report; semantic baseline experiment note;
  relevant `results/`; `PROJECT_STATE.md`, this board, and Week 1 summary.

Completion record (2026-07-27): froze normalized 384-dimensional mean-pooled
embeddings from `sentence-transformers/all-MiniLM-L6-v2` revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41` with Logistic Regression. On the
same 1,005-row locked validation set, accuracy was 0.900498 and macro-F1 was
0.898020, improvements of 0.034826 and 0.035371 over frozen W1-002. Exact
dependencies, provenance, aligned predictions, per-class/confusion evidence,
runtime, cache integrity, and matching fresh-cache rerun hashes are retained.
`test_evaluated=false` and `test_encoded=false`; official test remains W1-004.

### W1-004 — Evaluation, confusion/error analysis, and Week 1 P0 gate

- **Objective:** evaluate the two frozen baselines fairly, explain important
  fine-grained failures, and make an evidence-backed Week 1 gate decision.
- **Inputs:** locked W1-001 test IDs; frozen W1-002 and W1-003 predictions/configs;
  common evaluation code and error taxonomy.
- **Outputs:** final two-row benchmark; accuracy, macro-F1, per-class
  precision/recall/F1; confusion matrix/top confusion pairs; reviewed error cases
  covering semantic overlap, ambiguity/data issues, and likely model limitations;
  explicit `PASSED` or `FAILED/PARTIAL` gate decision and follow-up risks.
- **Acceptance criteria:** evaluation is a single controlled run on the untouched
  locked test; reported numbers reproduce from retained predictions/config; top
  confusions include representative examples and reasoned taxonomy; the report
  answers which baseline is better, where, and why; all Week 1 P0 checklist items
  are evidenced before Phase 2 or P1 can open.
- **Test/evidence:** evaluation tests/commands; machine-readable metrics and
  predictions; confusion figure/table; manual-analysis sample with stable IDs;
  completed Week 1 exit checklist. A failed gate is recorded honestly rather than
  converted into a pass.
- **Report updates:** today's daily report; evaluation/error-analysis experiment
  note; benchmark/confusion artifacts in `results/`; finalized
  `week_01_summary.md`; `PROJECT_STATE.md` and this board. No Week 2 task begins as
  part of this gate review.

Completion record (2026-07-27): preregistered and ran one primary plus one
byte-matching reproducibility evaluation of the two frozen candidates after
identical refits on all 10,003 non-test rows. On the 3,080-row official test,
lexical accuracy/macro-F1 was 0.878247/0.878362 and semantic was
0.908117/0.908075. Thirty bounded cases, paired outcomes, all 77 classes,
confusions, diagnostic confidence, runtime, and the seven-row overlap sensitivity
were analyzed. Frozen semantic MiniLM was selected; Week 1 P0 gate `PASS`.

## Week 2 executable task contracts

### W2-001 — Controlled synthetic KB specification/generation/validation

- **Objective:** build an English, versioned, fully synthetic KB for exactly ten
  locked Banking77 intents without starting gold mapping or retrieval.
- **Outputs:** intent definitions, JSON Schema/config, generation guideline,
  36 canonical JSONL documents, document/version plan, hard-negative matrix,
  deterministic validator, manifest/coverage evidence, and regression tests.
- **Acceptance criteria:** 28–36 documents; every intent has at least two eligible
  approved documents and two types; four complete version families; at least
  eight hard negatives; zero invalid references/status leakage/duplicates; fixed
  as-of eligibility; reproducible hashes and passing tests.
- **Boundary:** W2-002 queries/gold evidence and W2-003 retrieval remain separate
  tasks and were not started.

Completion record (2026-07-28): froze 36 fictional PayResolve Demo Bank documents
with 26/5/5 APPROVED/DRAFT/EXPIRED and 10/12/9/5 FAQ/Policy/Runbook/Escalation.
All ten intents have two or three eligible documents across at least two types.
Four version families, 12 hard-negative relationships, deterministic dataset hash
`e54a215...d4c88`, structurally hardened first-28 gate, full validator, and manual
review passed. Senior-review regression evidence includes 29 focused tests, nine
direct mutation failures with explicit codes, 56 full-suite tests, and passing
project reporting validation; canonical dataset bytes were unchanged.
Senior review verdict: `APPROVE_COMMIT`. W2-001 is DONE / REVIEWED / COMMITTED /
PUSHED in the current repository history. Week 2 P0 remains in progress.

### W2-002 — Gold evidence mapping

- **Objective:** freeze a manually reviewable, section-level evaluation mapping
  for the ten W2 intents without implementing retrieval.
- **Outputs:** 60 scenario-first English queries, 60 section-level mappings,
  deterministic validator/CLI, overlap audit, manifest/coverage artifacts,
  structured manual review, and mutation tests.
- **Acceptance evidence:** exact 10 development / 50 locked split and 50 ANSWER /
  10 ABSTAIN_ESCALATE; 26/26 eligible documents in active roles; 10/10
  ineligible documents as forbidden; four valid multi-document cases; zero
  exact/normalized query or Banking77 overlaps; validator PASS.
- **Boundary:** no embeddings, index, retriever, R0/R1, generation, API/UI, or P1.

Completion record (2026-07-28): scenario-first authoring was frozen before full
KB content mapping. Senior review then required direct-support and true
no-approved-evidence corrections. The corrected mapping has 56 gold, 50
acceptable, 50 hard-negative, and 10 forbidden section references. Nineteen gold
and acceptable roles changed, two ANSWER queries and ten safety probes were
rewritten, 43 focused tests passed, and seven direct mutations failed as expected.
Senior v2 review accepted all other corrections and the one residual role
inversion was patched. Review history: initial construction review → Senior
`FIX_REQUIRED` → direct-support/safety correction → validator hardening →
residual one-row role inversion → final patch → `APPROVE_COMMIT`. Status is
DONE / REVIEWED / COMMITTED / PUSHED.

### W2-003 — Controlled R0 vs R1 retrieval benchmark

- **Objective:** test whether the frozen predicted intent improves exact dense
  approved-evidence ranking through one soft boost and no other changed variable.
- **Frozen comparison:** 26 eligible documents / 52 section chunks, exact cosine,
  normalized MiniLM revision `1110a243...9b4d41`, top-k 3, and the W1-004
  final-fit semantic classifier.
- **Development:** lambda 0.15 selected from `{0.05, 0.10, 0.15, 0.20}` using
  strict MRR@3 and the preregistered tie-breaks.
- **Locked evidence:** R0 MRR@3 0.483333 versus R1 0.454167; paired R1 outcomes
  3 WIN / 4 LOSS / 33 TIE; all status/forbidden leakage metrics zero.
- **Decision:** retain simpler R0. Primary and reproducibility results matched
  exactly.
- **Review correction:** fixed empty-gold safety slicing; persisted 50 development
  ranking rows; separated 28 ANSWER errors from ten safety diagnostics; added the
  exact four-query multi-document slice; hardened cache-independent tracked
  verification and 19 targeted regression/mutation tests. The final taxonomy
  patch then made F rank-aware, expanded D to retained strict-gold success, and
  added seven row-semantic regression tests. All seven accepted numerical
  artifacts remain byte-identical; focused/full suites pass 56/56 and 155/155.
- **Review history:** initial completion → Senior `FIX_REQUIRED` for safety/error
  slicing and tracked verification → dev-ranking/verifier correction → Senior
  taxonomy `FIX_REQUIRED` → rank-aware taxonomy patch → final `APPROVE_COMMIT`.
- **Status:** DONE / REVIEWED / COMMITTED / PUSHED. Week 2 P0 gate PASSED;
  selected retriever remains R0.

## Week 3 executable task contracts

### W3-003-EV1-C2 — Portable runtime-binding correction

- **Objective:** preserve immutable C1 and frozen EV1 semantics while separating Git-portable integrity from external offline runtime readiness.
- **Acceptance:** bind 25 R-owned tracked inputs; verify 14 external assets; provision 11 exact snapshot files by ordinary copy; load exact MiniLM revision offline on CPU without encode/query/evaluation.
- **Authorization:** future A must be a one-path child of C2 and bind bundle SHA-256 plus bytes, asset-manifest SHA, C2-manifest SHA, C1/R identities, and Senior approval.
- **Boundary:** no commit/push, authorization, network, retrieval, generation, inference, PRIMARY, evaluation, reproduction, or finalization.
- **Status:** corrected uncommitted candidate awaits Senior review; W3 product gate and W4 remain blocked.


### W3-001 — Grounded Pipeline + Evidence Gate

- **Objective:** build an offline deterministic R0-based pipeline that answers
  only from approved/effective evidence or returns a generic safe escalation.
- **Development contract:** exactly ten frozen W2 development ANSWER queries and
  ten new scenario-first negative probes; select from the preregistered 4×3 gate
  grid without using W2 locked or Week 3 critical outcomes.
- **Outputs:** approved-only context builder, evidence gate, extractive generator,
  claim/citation verifier, two response modes, tracked development artifacts,
  reproducibility evidence, tests, and review reports.
- **Boundary:** W3-002, critical evaluation, formal ablations, external LLMs,
  API/UI, hybrid retrieval, rerankers, and P1 remain NOT STARTED.
- **Implementation record (2026-07-29):** implemented the offline R0 pipeline,
  approved/effective context boundary, deterministic gate, extractive generator,
  exact-quote citation verifier, tracked verifier, and 69 focused tests. The
  20-case development grid selected `S0.40_C0.45`; it has zero unsafe answers
  but abstains on all positives. Primary and reproduction outputs are
  byte-identical. Senior review found vacuous citation metrics, relevance-blind
  positive success, unbound citation metadata, and hard-coded generator weights;
  these are corrected without changing the frozen policy or output bytes.
- **Experiment verdict:** the preregistered gate-v1 experiment completed, but its
  selected policy is not a usable production candidate because it abstains on
  every positive development query.
- **Review lifecycle:** initial implementation → Senior `FIX_REQUIRED` → citation
  metadata binding → evidence relevance metrics → non-vacuous citation metrics
  → config-driven generator weights → Senior `APPROVE_COMMIT — PARTIAL BASELINE`.
- **Status:** implementation `DONE / REVIEWED / ACCEPTED`; evidence-gate result
  `PARTIAL — UTILITY NOT DEMONSTRATED`; overall `PARTIAL / REVIEWED / ACCEPTED`.
  W3-001-CR1 is `DONE / REVIEWED / ACCEPTED` with a qualified post-hoc PASS.
  W3-002's numerical run was subsequently preserved but its critical-set integrity
  was invalidated; the model verdict is not established. Week 3 P0 is `BLOCKED /
  IN PROGRESS` and Week 4 is `BLOCKED / NOT STARTED`.

### W3-001-CR1 — Evidence Gate Utility Recovery v2

- **Authorized objective:** recover useful grounded answers without weakening the
  accepted approved-only, extractive, citation, ambiguity, or override contracts.
- **Preregistered hypothesis:** exact IDF token coverage underestimates support
  across common banking paraphrases; canonical support plus requested-dimension
  matching can recover utility, while an unsupported-specificity guard prevents
  strongly overlapping but unsupported detail requests from passing.
- **Evaluation boundary:** select only on the observed frozen 20-case design set;
  freeze a new 10 ANSWER / 10 ABSTAIN holdout before execution; run holdout once
  plus one reproduction; never tune from holdout outcomes.
- **Frozen selection:** `S0.40_C0.20`; design only, with zero holdout IDs used.
- **Holdout result:** gate v1 resolved 1/10 positives (recall 0.10; safe resolution
  0.55); gate v2 resolved 6/10 positives (recall 0.60; safe resolution 0.80),
  covered transfer/card-payment/cash-withdrawal, and retained negative abstention
  1.00 and unsafe-answer rate 0.00.
- **Hard failure:** gate v2 produced one positive wrong-evidence answer
  (`Q_V2_HOLD_TR_PEND_001`). Unsupported claims, DRAFT/EXPIRED citations, and
  citation metadata failures remained zero, but the preregistered hard safety
  requirements therefore failed.
- **Reproducibility:** primary and reproduction outputs are byte-identical; tracked
  verification passed; focused/full tests passed 47/47 and 271/271.
- **Mapping adjudication:** all ten positives were reviewed against all 52 eligible
  approved sections. Exactly three mappings omitted one direct-support section.
  The immutable original mapping/result remains FAILED; a Senior-approved three-row
  overlay applied only to post-holdout relevance metrics yields PASS.
- **Senior verdict:** `APPROVE_COMMIT — QUALIFIED POST-HOC PASS`.
- **Status:** implementation DONE / REVIEWED / ACCEPTED; adjudicated evaluation
  PASS / REVIEWED / ACCEPTED. W3-002's original run is preserved, but the
  critical set is invalidated and its model verdict is not established.

### W3-002 prerequisite — mapping-quality gate

Before critical evaluation: (1) author and freeze the critical set; (2) audit every
positive query against all 52 eligible approved sections; (3) freeze the complete
direct-support evidence set; (4) record a pre-evaluation mapping-audit SHA-256;
and (5) do not execute while any mapping omission remains. This safeguard passed
before inference: 40/40 positive and 20/20 negative audits covered all 52 eligible
sections with zero unresolved omissions or false-no-answer labels. The frozen
evaluation's reported numerical verdict was subsequently invalidated because the
audit itself was self-referential. No replacement evaluation is authorized; Week
4 remains blocked.

### W3-002 integrity incident containment

- **Senior verdict:** `APPROVE_COMMIT — INTEGRITY INCIDENT EVIDENCE`.
- **Implementation:** DONE / REVIEWED / ACCEPTED.
- **Original numerical run:** DONE / PRESERVED AS HISTORICAL DIAGNOSTIC EVIDENCE;
  primary and reproduction remain internally consistent.
- **Original evaluator-reported result:** FAILED UNDER INVALID MAPPING CONTRACT.
- **Critical-set integrity:** INVALIDATED — pre-evaluation mapping audit was
  self-referential.
- **Model/pipeline verdict:** NOT ESTABLISHED.
- **Post-hoc scope:** 20 positive mapping defects, two hard negatives providing
  direct support, six over-constrained exact-ID multi-document mappings, and
  eight false ABSTAIN labels.
- **Obligation-cover correction:** all six original multi-document labels are
  over-constrained. `A_003`, `A_020`, and `A_040` need one section. `A_016`,
  `A_028`, and `A_036` need two semantic sections but can be answered entirely
  within one approved escalation document. No reviewed query was proven to need
  two distinct documents.
- **Audit repair:** original self-certifying path rejects execution; independent
  support judgments, 52-section row validation, valid-cover enumeration, and
  recomputed hard-negative/summary consistency are required.
- **Integrity incident analysis:** DONE / REVIEWED / ACCEPTED.
- **Boundary:** no `critical_eval_v2`, encoder/retrieval/pipeline rerun, model
  selection, or Week 4 work is authorized.

### W3-002-CR1 contract-amendment gate — 2026-08-05

- **Senior verdict:** `APPROVE_CONTRACT_AMENDMENT — OPTION A`.
- **Task status:** `DONE / REVIEWED / COMMITTED / PUSHED`.
- **Committed SHA:** `22e8b38ae28e86537ece8aa892f39c35b517e74b`.
- **Candidate revision 4:** `REJECTED / PRESERVED AS REVIEW HISTORY`.
- **Feasibility result:** 15 `ANSWER / SAFE_CORRECTIVE`, 5
  `ABSTAIN_ESCALATE`; fixed 40/20 distribution is not semantically feasible
  with the frozen KB.
- **Integrity:** `structural_integrity_verified=false`,
  `pre_evaluation_integrity_passed=false`, semantic approval=false,
  evaluation authorization=false, critical evaluated=false.
- **Approved decision:** retain top-level `ANSWER`/`ABSTAIN_ESCALATE`, add
  `answer_subtype=STANDARD|SAFE_CORRECTIVE`, and use the audited 40/15/5
  distribution.
- **State at contract-amendment commit:** candidate revision 5 was `NOT CREATED`;
  authoring required a separate Senior-reviewed contract.
- **Current boundary:** the separately authorized revision-5 candidate is now
  structurally frozen, but inference, evaluation, W3-002 execution, and Week 4
  remain unauthorized.
- **Decision-review bundle:** PREPARED outside the repository with a 20-row
  safety-challenge contract, explicit minimal corrective covers, approved/effective
  evidence catalog, five enriched hard-negative proposals, preservation payload,
  detached inventory, and a standard-library standalone verifier. Its approved
  SHA-256 is
  `bc7317000005859f2e4b215cf0c4f687e5e284a4a004270d81f9f5abd0074786`.

The formalized contract separates control-plane from evidence-cited factual
claims, defines the evaluator outcomes and denominators, and records a future
revision-5 checklist without creating candidate data. Rejected revisions 2/3/4
remain byte-preserved. Senior semantic approval, evaluation authorization, and
critical evaluation remain false; model verdict is `NOT_ESTABLISHED`; Week 3 P0
and Week 4 remain blocked.

### W3-002-CR1 candidate revision 5 authoring — 2026-08-06

- **Senior task verdict:** `APPROVE_OPEN_TASK — CANDIDATE REVISION 5 AUTHORING`.
- **Task status:** `AUTHORED / FROZEN / STRUCTURALLY VERIFIED / AWAITING SENIOR
  SEMANTIC REVIEW`.
- **Authorized:** candidate authoring and structural-only verification.
- **Not authorized:** Senior semantic approval, model/encoder loading, retrieval,
  generation, critical evaluation, staging, commit, push, or Week 4 work.
- **Lifecycle:** `senior_semantic_review_approved=false`,
  `evaluation_authorized=false`, `critical_evaluated=false`, model verdict
  `NOT_ESTABLISHED`, Week 3 P0 `BLOCKED / IN PROGRESS`, Week 4 `BLOCKED / NOT
  STARTED`.
- **Frozen candidate:** 60 query rows, 3,120 independent Pass-B judgments,
  distribution 40 `ANSWER / STANDARD`, 15 `ANSWER / SAFE_CORRECTIVE`, 5
  `ABSTAIN_ESCALATE`; model-input byte changes from revision 4: 0/60.
- **Structural evidence:** focused revision-5 tests 84/84 PASS; contract tests
  11/11 PASS; feasibility source tests 14/14 PASS; related integrity tests 68/68
  PASS; isolated application suite 471/471 PASS with 5 skips.
- **Next task:** independent Senior semantic review of the frozen revision-5
  candidate and review bundle. Evaluation remains prohibited until separately
  authorized after approval.

### W3-002-CR1 candidate revision 6 semantic correction — 2026-08-06

- **Senior verdict on revision 5:** `FIX_REQUIRED`.
- **Revision 5:** `REJECTED / PRESERVED AS REVIEW HISTORY`; 19/19 archived
  artifacts verified byte-for-byte.
- **Revision 6:** `FROZEN_CANDIDATE / AWAITING_SENIOR_SEMANTIC_REVIEW`.
- **Scope:** structural-only correction; 60 model inputs and the Option A 40/15/5
  distribution remain frozen.
- **Structural evidence:** focused tests 99/99 PASS; Option A contract tests
  11/11 PASS; feasibility source tests 14/14 PASS; related integrity tests 68/68
  PASS; isolated tracked application suite 486/486 PASS with 5 skips.
- **Semantic delta:** one Pass-B semantic row changed: `Q_V2_A_CSD04` ×
  `ESC_CASH_UNRECOG_001#immediate_trigger`, `PARTIAL_SUPPORT` to
  `DIRECT_SUPPORT`, adding requested obligation `SECURITY`.
- **Lifecycle:** candidate bytes frozen, structural and pre-evaluation integrity
  verified with scope `STRUCTURAL_ONLY_SEMANTIC_APPROVAL_PENDING`;
  `senior_semantic_review_approved=false`, `evaluation_authorized=false`,
  `critical_evaluated=false`, `model_verdict=NOT_ESTABLISHED`.
- **Next task:** independent Senior semantic review of revision 6. Inference and
  evaluation remain prohibited.

### W3-002-CR1 revision 6 semantic approval — 2026-08-06

- **Senior verdict:** `APPROVE_SEMANTIC_INTEGRITY — REVISION 6`.
- **Current state:** `FROZEN_CANDIDATE /
  SENIOR_SEMANTIC_REVIEW_APPROVED / COMMITTED / PUSHED`.
- **Candidate commit:** `d27de987d0eb7a942c88590eec9a30bdd6ee33d8`.
- **Candidate manifest SHA-256:**
  `2f42fb4ff7159ef2735ce88418b0dbfcc414b0091476f1882a83d13e807002ad`.
- **Approval scope:** `FROZEN_CANDIDATE_BYTES_ONLY`; candidate revision 6 may be
  committed, but no candidate byte may change after approval.
- **Lifecycle:** `senior_semantic_review_approved=true`,
  `evaluation_authorized=false`, `critical_evaluated=false`,
  `model_verdict=NOT_ESTABLISHED`.
- **Boundary:** evaluation requires a separate authorization task and model
  performance remains not established.
- **Next task:** W3-002-CR1 evaluation authorization — `NOT STARTED / REQUIRES A
  SEPARATE SENIOR-REVIEWED TASK`.
- **Phase gates:** Week 3 P0 remains `BLOCKED / IN PROGRESS`; Week 4 remains
  `BLOCKED / NOT STARTED`.

### W3-002-CR1 candidate revision 7 semantic correction — 2026-08-10

- **Senior trigger:** COV1 reopened candidate semantics; revision 6 is
  `SEMANTICALLY_APPROVED_AT_THE_TIME / SUPERSEDED_PRE_EVALUATION_BY_COV1`.
- **Senior verdict:** `APPROVE_SEMANTIC_INTEGRITY — CANDIDATE REVISION 7`.
- **Task status:** `FROZEN_CANDIDATE / SENIOR_SEMANTIC_REVIEW_APPROVED /
  COMMITTED / PUSHED`.
- **Candidate commit:** `18a1840f39fef8f07337ff357f7991292389bae9`;
  exactly 37 Senior-reviewed paths were committed and pushed.
- **Exact semantic delta:** four Pass-B obligation assignments changed and zero
  unexpected semantic rows changed: TRD01 POL/RUN lose `BOUNDARY`, TRR02 ESC
  loses `TRACE`, and CSU03 ESC loses `PROHIBIT`; each retains its remaining
  direct obligation.
- **Derived mapping:** 92 complete covers. Invalid TRD01 POL/RUN, TRR02 ESC, and
  CSU03 ESC-only covers are absent; the Senior-required replacement covers exist.
- **Frozen invariants:** 60/60 model inputs unchanged; distribution remains 40
  STANDARD / 15 SAFE_CORRECTIVE / 5 ABSTAIN; support classes remain 179 direct,
  6 partial, 1,452 contextual, and 1,483 irrelevant; five hard negatives remain.
- **Lifecycle:** `senior_semantic_review_approved=true` via the separate Senior
  approval record,
  `evaluation_authorized=false`, `critical_evaluated=false`,
  `model_verdict=NOT_ESTABLISHED`.
- **EA1:** `FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_AUTHORIZATION_REVIEW`.
  Senior clarified that the candidate freezes minimum-cardinality canonical
  covers. Production and independent brute-force derivations now match all 55
  answerable queries and all 92 frozen canonical covers. Four valid larger
  inclusion-minimal covers remain explicit noncanonical diagnostic evidence.
- **Safety evidence:** six COV1 cases pass 6/6; the 150-case target-specific
  matrix has zero false positives and zero false negatives.
- **Boundary:** candidate revision 7 remains immutable; no model, retrieval,
  generation, inference, evaluation, staging, commit, push, or Week 4 work is
  authorized by this readiness task.
- **Next task:** independent Senior review of the frozen EA1 readiness package.
  `evaluation_authorized=false`, `critical_evaluated=false`, and
  `model_verdict=NOT_ESTABLISHED` remain authoritative.

### W3-002-CR1-EA1 readiness revision 8 — 2026-08-11

- **Senior verdict on readiness revision 7:** `FIX_REQUIRED`; the package is
  `REJECTED_BY_SENIOR / SAFETY_AND_AUTHORIZATION_HARDENING_REQUIRED` and its ZIP
  hash is `dc72ab6d074c3dd3eb3391586ec783c8b287abbb44114e872e048c4cf5c9757c`.
- **Candidate boundary:** Candidate Revision 7 remains frozen, Senior-approved,
  committed, and pushed. Candidate Revision 8 is absent.
- **Revision-8 correction:** deterministic safe-negative morphology,
  target/value ordering in both directions, negative-status payload detection,
  occurrence-local precedence, current-day authorization topology, and
  occurrence-level stale-binding classification.
- **Evidence:** 22/22 exact Senior cases, 206-case expanded matrix with zero
  FP/FN, 27/27 observed mutations rejected at expected layers, and eight of
  eight real self-adversarial categories pass.
- **Status:** `FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_AUTHORIZATION_REVIEW`.
  Evaluation remains unauthorized and the model verdict remains not established.

### W3-002-CR1-EA1 readiness revision 9 — 2026-08-11

- **Senior verdict on readiness revision 8:** `FIX_REQUIRED`; the readiness
  package is `REJECTED_BY_SENIOR / DISCLOSURE_TARGET_COVERAGE_INCOMPLETE /
  ADVERSARIAL_FIXTURE_TARGET_CONSTRUCTION_INVALID`. Its ZIP SHA-256 is
  `3291975173dff7e8afb0da4ab368d32e8f1913020bc9951f5e56b3b8686fe218`.
- **Candidate boundary:** Candidate Revision 7 remains frozen, Senior-approved,
  committed, and pushed. Candidate revisions 8 and 9 are absent.
- **Revision-9 correction:** all 15 SAFE_CORRECTIVE rows have explicit target
  classes; eight disclosure-capable queries expose 11 canonical disclosure
  targets to an occurrence-local grammar.
- **Evidence:** 38/38 Senior regressions pass; the 256-case matrix has zero
  FP/FN; 176 disclosure fixtures have zero malformed constructions; every
  disclosure-capable query has target-first, payload-first, refusal-plus-payload,
  and negative-status-plus-payload coverage; 30/30 mutations are rejected; all
  eight self-adversarial categories pass.
- **Status:** `FROZEN_READINESS_PACKAGE / AWAITING_SENIOR_AUTHORIZATION_REVIEW`.
  `evaluation_authorized=false`, `critical_evaluated=false`, and
  `model_verdict=NOT_ESTABLISHED` remain authoritative.

## W3-002-CR1-EA1-REV10 — Week 3 P0

- **Description:** Close EA1 post-freeze subtype separation, narrow disclosure
  guard, and raw execution provenance before evaluation authorization.
- **Priority:** P0.
- **Status:** `SENIOR_REVIEWED / F3_BATCH_MEMBERSHIP_DEFECT_FOUND`.
- **Findings:** `F1_POST_FREEZE_SUBTYPE_SEPARATION=CLOSED`,
  `F2_NARROW_DISCLOSURE_GUARD=CLOSED`,
  `F3_ROW_PROVENANCE=CLOSED`; batch membership remained incomplete.
- **Evidence:** focused 20/20 PASS; settled readiness 118/118 PASS; exact registry
  8 queries/11 targets with zero enumerated literals; provenance enforced at
  persistence/freeze/pre-gold boundaries; active readiness verifier PASS.
- **Candidate:** Revision 7 remains frozen, Senior-approved, committed, pushed,
  and byte-verified 23/23. Candidate revisions 8/9/10 were not created.
- **Lifecycle:** EA1 Revision 10 is `SENIOR_REVIEWED /
  F3_BATCH_MEMBERSHIP_DEFECT_FOUND`; reason
  `RAW_BATCH_EXACT_MEMBERSHIP_NOT_ENFORCED_PRE_PERSISTENCE`;
  `evaluation_authorized=false`,
  `critical_evaluated=false`, `model_verdict=NOT_ESTABLISHED`.
- **Blocked:** Week 3 P0 remains `BLOCKED / IN PROGRESS`; Week 4 remains
  `BLOCKED / NOT STARTED`.

## W3-002-CR1-EA1-REV11 — Week 3 P0

- **Description:** close only exact raw batch membership at persistence, freeze,
  and pre-gold boundaries.
- **Priority:** P0.
- **Status:** `FROZEN_READINESS_PACKAGE /
  AWAITING_SENIOR_AUTHORIZATION_REVIEW`.
- **Findings:** `F1_POST_FREEZE_SUBTYPE_SEPARATION=CLOSED`,
  `F2_NARROW_DISCLOSURE_GUARD=CLOSED`, `F3_ROW_PROVENANCE=CLOSED`, and
  `F3_BATCH_MEMBERSHIP_PROVENANCE=CLOSED`.
- **Invariant:** rows=60, unique query IDs=60, and raw query-ID set equals the
  frozen runtime-payload query-ID set; accepted batches then reuse the existing
  per-row provenance validator.
- **Evidence:** F3-J…N 5/5 PASS; REV10 20/20 PASS; settled readiness 118/118
  PASS; active readiness verifier PASS. No inference or evaluation ran.
- **Candidate:** Revision 7 remains immutable and byte-verified 23/23. Candidate
  revisions 8/9/10/11 were not created.
- **Lifecycle:** `evaluation_authorized=false`, `critical_evaluated=false`,
  `model_verdict=NOT_ESTABLISHED`; Week 3 and Week 4 remain blocked.

## W3-002-CR1-EA1-REV12-AUTH-DATE — Week 3 P0

- **Description:** amend only the reviewed authorization daily-report path from
  `reports/week_03/daily/2026-08-11.md` to
  `reports/week_03/daily/2026-08-12.md`.
- **Priority:** P0.
- **Status:** `SENIOR EXECUTION READINESS APPROVED / COMMITTED / PUSHED` as R2
  `cec29477e3c75d132b54f787ba602a0a1b33f578`.
- **Reason:** `AUTHORIZATION_DAILY_REPORT_DATE_ROLLOVER`.
- **Candidate Revision 7:** `FROZEN / SENIOR SEMANTIC APPROVED / COMMITTED /
  PUSHED`; no Candidate Revision 8/9/10/11/12 exists.
- **EA1 Revision 11:** `SENIOR_EXECUTION_READINESS_APPROVED / COMMITTED /
  PUSHED / SUPERSEDED_ONLY_BY_AUTHORIZATION_DATE_TOPOLOGY_AMENDMENT` at
  `c7bc68bbef51684f6ff4ab7a672ca78af4cbbadd`; not rejected.
- **Scope:** exact five-path authorization allowlist, focused AUTH-DATE-01…05,
  and mechanical readiness hash rebinding only. F1/F2/F3 semantics remain
  closed and immutable.
- **Lifecycle:** `evaluation_authorized=false`, `critical_evaluated=false`,
  `model_verdict=NOT_ESTABLISHED`; Week 3 is `BLOCKED / IN PROGRESS`; Week 4 is
  `BLOCKED / NOT STARTED`.
- **Next:** review the separately authored exact five-file authorization commit
  A candidate. Any real A commit remains a separate task and must satisfy
  `parent(A)=R2`.

## W3-002-CR1-EA1-AUTH-A — Week 3 P0

- **Description:** authorize exact Candidate Revision-7 and EA1 Revision-12
  committed execution bytes through separate commit A.
- **Priority:** P0.
- **R2:** `cec29477e3c75d132b54f787ba602a0a1b33f578`; EA1 Revision 12 is
  `SENIOR EXECUTION READINESS APPROVED / COMMITTED / PUSHED`.
- **Exact authorization scope:** authorization record, `PROJECT_STATE.md`, `TASKS.md`,
  Week-3 summary, and `daily/2026-08-12.md` only.
- **Authorization:** `AUTHORIZED_FOR_PRIMARY_EXECUTION`;
  `evaluation_authorized=true`, `critical_evaluated=false`, and
  `model_verdict=NOT_ESTABLISHED`.
- **Boundary:** do not mark W3-002-CR1 done. Primary execution must wait for
  Senior to independently verify committed `HEAD=A` and `HEAD^=R2`; no inference
  or critical evaluation has occurred.

### Deferred — Hybrid / structured disclosure hardening

- `DEFERRED / NOT A WEEK-3 P0 BLOCKER`.
- Possible future scope: richer structured metadata, evidence-status-driven
  disclosure semantics, generalized relation handling, and a public structured
  API only if Week-4 requirements separately authorize it.

## W3-002-CR1-EA1-READINESS-R13 — Week 3 P0

- **Status:** `STOPPED / UNEXPECTED_ENVIRONMENT_DRIFT`; not ready for Senior review.
- **Implemented:** `HF_HUB_OFFLINE=1`, production `local_files_only=True`, exact snapshot verification, and hash binding for nine transitive runtime modules.
- **Evidence:** Candidate 23/23, snapshot 11/11, payload 60/60, focused 15/15, readiness 118/118, Rev10/11/12 30/30, Senior safety 3/3, full harness 655/655 PASS.
- **Stop evidence:** expected 299 distributions/fingerprint `83b21cc...`; observed 300/fingerprint `a3689c...`. Core ML versions match, but the strict full-environment gate does not.
- **Authorization:** R13 `evaluation_authorized=false`; A12 fails closed. Reset is `NOT EXECUTED`; no inference/evaluation ran. The pre-stop ZIP is non-deliverable. Week 3 and Week 4 remain blocked.

### W3-002-CR1-EA1-R13-ENV-FP-FIX-01 — 2026-08-12

- **Priority:** P0.
- **Status:** DONE / READY FOR SENIOR READINESS REVIEW.
- **Result:** shared readiness/runtime canonical third-party identity is invariant across C1/C2/C3/C4 at 298 rows and SHA-256 `39c1c4a09994f3ea0b7691c796b39085f95fb985efa73207057fa5f7c187f25a`.
- **Safety:** conflicting versions fail closed; local `payresolve-ai` remains source-hash-bound but excluded from third-party identity; core five versions and metadata hashes are bound explicitly.
- **Verification:** all ordered suites pass, including 667/667 full harness; offline synthetic probe has zero network attempts and exact expected embedding SHA.
- **Boundary:** no package mutation, Candidate mutation, reset, authorization, primary/evaluation, stage, commit, or push.

### W3-002-CR1-EA1-R13-BINDING-FIX-01 — 2026-08-13

- **Priority:** P0.
- **Status:** DONE / `R13_BINDING_FIX_READY_FOR_SENIOR_REVIEW`.
- **Result:** authorization now binds the deterministic stable environment identity and its reviewed artifact; runtime verifies the live identity against both reviewed and authorized identities before constructing the model.
- **Closure:** all 18 modules on the bounded local production path are documented, SHA-256-bound, and verified; exclusions are limited to empty package initializers.
- **Negative controls:** ENV-AUTH 01–07 plus tampering of `generation/verification.py`, `data/banking77.py`, and `generation/citations.py` all fail closed pre-model; detached bundle verifier includes environment-contract-only and candidate-binding-only mutation cases.
- **Verification:** offline probe 131.649789 seconds with zero network attempts; all ordered suites pass; corrected full repository harness 679/679 in 299.132 seconds.
- **Boundary:** no Candidate/E1 mutation, reset, authorization, primary/evaluation, stage, commit, or push.

### W3-002-CR1-EA1-R13-AUTH-DATE-CLOSURE-01 — 2026-08-13

- **Priority:** P0.
- **Status:** DONE / `R13_FINAL_READY_FOR_SENIOR_REVIEW`.
- **Result:** active R13 future-A13 topology is exactly five paths and uses only `reports/week_03/daily/2026-08-13.md`; active 2026-08-12, older, future, missing, duplicate-date, and source/Candidate mutations fail closed.
- **Historical boundary:** Revision-12 retains 2026-08-12 semantics through an explicit historical fixture, not the active R13 config.
- **Closure:** all nine enforcement functions remain in the authorization-bound root execution module; complete runtime closure remains 18 modules with no new dependency.
- **Verification:** ordered suites pass; corrected full harness 688/688 in 225.925 seconds; offline diagnostic 9.976939 seconds with zero network attempts and unchanged embedding SHA.
- **Boundary:** no Candidate/E1 mutation, reset, A13 record, authorization, primary/evaluation, stage, commit, or push.

### W3-002-CR1-EA1-R13-REVIEW-COVERAGE-FIX-01 — 2026-08-13

- **Priority:** P0.
- **Status:** DONE / `R13_REVIEW_COVERAGE_FIXED_READY_FOR_SENIOR_REVIEW`.
- **Correction:** bind the omitted R13-owned `tests/test_retrieval_benchmark.py` into readiness/authorization review hashes and the final bundle without adding it to the 18-module runtime closure.
- **Safety:** the single changed test is stricter, preserves all R0/R1 semantics, and detects frozen Week-2 implementation provenance drift without loading cache/model/encoder.
- **Coverage guard:** deterministic classification and commit dry-run require every R13-reviewed dirty byte to exist identically in bundle `task_files`; protected E1, review ZIP, and user-owned paths are excluded.
- **Verification:** coverage 6/6, retrieval 56/56, final exact-byte full harness 694/694 in 237.471 seconds, final regenerated offline diagnostic 45.061138 seconds with zero network attempts.
- **Boundary:** staged 0; commit/push none; no Candidate/E1/runtime semantic mutation, reset, authorization, or primary/evaluation.

## W3-002-CR1-EA1-R14-AUTH-VERIFIER-HARDENING — Week 3 P0

- **Reason:** post-R13 A13 authoring aborted fail-closed after proving the production verifier accepted a wrong `readiness_revision` and a non-empty subset of the exact five authorization paths.
- **Scope:** enforce complete final-authorization lifecycle fields, require exact five-path equality, add R14 field/topology regressions, regenerate active R14 readiness bindings/evidence, and build a detached review bundle.
- **Preserved:** Candidate Revision 7, R13 history, A12/E1 incident archive and reset receipt, reviewed environment identity, and all primary/evaluation absences.
- **Verification:** exact-field/topology controls PASS; ordered matrix 88/88 in 23.562s; readiness 118/118 in 68.984s; Senior safety 68/68; retrieval 56/56; corrected repository harness 703/703 in 293.8s process time; offline probe 17.945591s with zero network attempts.
- **State:** DONE / `R14_READY_FOR_SENIOR_REVIEW`; A13 not created; A14 not created; `evaluation_authorized=false`; PRIMARY not authorized.

### W3-002-CR1-EA1-A14-AUTHORIZATION — proposed transition

- **R14 binding:** `c0afb7ba74cbcb778a5952399f1db628166df40d`; R14 is Senior readiness-approved, committed, and pushed.
- **State:** `AUTHORIZED_FOR_PRIMARY_EXECUTION`; Candidate Revision 7 remains frozen/Senior-approved/committed/pushed; A13 was not created.
- **Boundary:** `evaluation_authorized=true`, `critical_evaluated=false`, `model_verdict=NOT_ESTABLISHED`; PRIMARY NOT YET RUN. Week 3 blocked/in progress; Week 4 blocked/not started.
- **Next:** Senior verifies committed A14 topology before PRIMARY.

### W3-002-CR1-EA1-R15-EVALUATION-STATE-INPUT-CLOSURE — Week 3 P0

- **Status:** DONE / `R15_READY_FOR_SENIOR_REVIEW`.
- **Fix:** canonical six-input evaluator closure at indexes 4 and 9; 12/12 transition contracts exact.
- **Continuation:** exact legacy fingerprints, 7/7 PRIMARY hashes, absent reproduction/final outputs, write-once receipt, authorization rebinding, and distinct historical/future runtime paths are tested on isolated copies.
- **Verification:** focused 7/7; EA1 Rev10–15/readiness 169/169; full executable suite 792 passed, 5 skips, 116 subtests.
- **Boundary:** no active state/runtime mutation, rerun, A15, stage, commit, or push.

#### F1 — continuation authority production binding

- **Status:** DONE / `R15_CORRECTED_READY_FOR_SENIOR_REVIEW`.
- Arbitrary authority dictionaries are rejected; migration internally requires production-verified committed A15 authority and exact continuation fields.
- One-shot CLI, PREPARED/PASS transaction receipt, 16 required negative controls, and committed synthetic A15 positive control are covered.

#### F2 — synthetic Git-config isolation

- **Status:** DONE / `R15_F2_CORRECTED_READY_FOR_SENIOR_REVIEW`.
- Linked-worktree common-config mutation is reproduced in a disposable repository for local identity and `core.autocrlf`.
- Real local identity is restored; synthetic commits use command-local identity/config, with exact common-config guards at six phases.
- Local `core.autocrlf=false` is unchanged and flagged for Senior review. Active state/runtime and PRIMARY remain exact; reproduction not retried; staged 0; commit/push none.

#### F3 — post-push committed-byte closure

- **Status:** CORRECTED / AWAITING SENIOR REVIEW.
- **Finding:** `R15_POST_PUSH_COMMITTED_BYTE_CLOSURE_MISMATCH`; exactly four of 62 candidate hash-bound paths differ in initial R15 commit `5e89ec1`.
- **Correction:** propose a new Revision-15 corrective readiness commit containing the exact reviewed omissions and a fail-closed committed-tree/scope verifier. Historical commit `5e89ec1` remains immutable.
- **Boundary:** A15 unauthorized; no migration, reproduction, PRIMARY, stage, real commit, or push.

### W3-002-CR1-EA1-A15-AUTHORIZATION-AUTHORING — Week 3 P0

- **Status:** PROPOSED / `A15_AUTHORIZATION_READY_FOR_SENIOR_REVIEW`.
- **Binding:** exact five-path A15 child of Senior-approved R15-F3 `a8dc336b73be6ec91b2280c56c048d348329cff5`; no future A15 commit SHA is self-referenced.
- **Authority:** exact continuation lineage and one-shot `R14_PRIMARY_EVALUATED_TO_R15_CONTINUATION`; `evaluation_authorized=true`, `critical_evaluated=false`, `model_verdict=NOT_ESTABLISHED`.
- **Evidence boundary:** synthetic committed A15 production verification, fail-closed negative controls, isolated PREPARED→PASS migration, and pre-model Repro V0 gate only.
- **Preserved:** Candidate Revision 7, R15-F3 bytes, historical PRIMARY/state/runtime, and real workspace runtime state. PRIMARY was not rerun; reproduction/finalization were not run.
- **Next:** Senior reviews A15; only after a real committed A15 and successful production migration may a separately authorized reproduction retry be considered.


## A16 post-evaluation continuation authorization

- The real R15-F4-F1 comparator implementation correction is committed and pushed as `e6b49d4db4658251d68692aba812ad080ce5b3e1`.
- The real lifecycle state remains `REPRO_EVALUATED`; the frozen raw reproduction behavioral evidence remains `180/180` and substantively matches PRIMARY.
- A16 authorizes only the post-evaluation continuation required to bind the committed R15-F4-F1 readiness implementation before reproducibility verification.
- No model or evaluator rerun is authorized. Real `verify-reproducibility` has not run, finalization has not run, and the model verdict remains `NOT_ESTABLISHED`.
- This authoring package does not claim `REPRO_VERIFIED`, `FINALIZED`, Week 3 P0 completion, or model approval.


## W3-002-CR1-EA1 A17 post-verify continuation authorization — 2026-08-16

- R15-F5-F1 is published as `328757ffd768ce9603b3ee596f74505afa1b4a4c`.
- At A17 authoring time, the real lifecycle was `REPRO_VERIFIED` with history length 11; reproducibility was provenance-valid and behaviorally identical for 180/180 rows.
- A17 authorizes only `R15_F5_POSTVERIFY_CONTINUATION` to bind the corrected finalization implementation to the existing verified evidence.
- At that authoring milestone, real post-verify continuation, finalization, and `verify-results` had not run and the final summary was absent; those steps subsequently completed under separate Senior authorizations.
- Before finalization, `critical_evaluated=false` and `model_verdict=NOT_ESTABLISHED`; A17 alone does not establish model approval or complete the Week 3 P0 gate.
- Candidate Revision 7, PRIMARY, reproduction, comparison, and historical lifecycle evidence remain immutable.

## W3-002-CR1-EA1-SRD1 — Senior result decision record

- **Priority:** P0.
- **Status:** `DONE / READY FOR SENIOR REVIEW`.
- **Technical integrity:** `DONE / FINALIZED / VERIFY_RESULTS_PASS`; lifecycle
  state is `FINALIZED`, history length is 12, and PRIMARY/REPRO equality is
  180/180.
- **Senior model/pipeline verdict:**
  `NOT_APPROVED_FOR_PRODUCT_INTEGRATION — REMEDIATION_REQUIRED`.
- **Selected variant:** none. V0 is `REJECT_LOW_UTILITY_OVER_ABSTENTION`, V1 is
  `REJECT_NO_END_TO_END_GAIN`, and V2 is
  `REJECT_UNSAFE_AND_ABSTAIN_FAILURE`.
- **Gate status:** W3 evaluation work is complete, but the W3 P0 product gate is
  `NOT_CLOSED_REMEDIATION_REQUIRED`; W4 real AI integration is `BLOCKED`.
- **Locked boundary:** Candidate Rev7 and frozen PRIMARY/REPRO evidence remain
  immutable and must not become tuning data or be rerun as a fresh holdout.
- **Next:** plan `W3-003 — Grounded RAG Behavior Remediation` using separate
  development/regression evidence. Implementation and any independent
  reevaluation require separate authorization.
