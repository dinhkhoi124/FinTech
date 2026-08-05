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
| W3-002-CR1 | 3 | P0 | Pristine Critical Evaluation Recovery | Option A contract approved and formalized; revisions 1–4 preserved; revision 5 not created; semantic/evaluation approval false | CONTRACT AMENDMENT APPROVED / AWAITING SENIOR COMMIT REVIEW |
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
- **Task status:** `CONTRACT AMENDMENT APPROVED / AWAITING SENIOR COMMIT REVIEW`.
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
- **Boundary:** no candidate revision 5, inference, evaluation, staging, commit,
  push, W3-002 execution, or Week 4 work is authorized.
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
