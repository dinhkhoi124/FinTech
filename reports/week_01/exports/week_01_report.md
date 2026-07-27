<!-- GENERATED FILE: edit canonical sources, not this aggregate. -->
<!-- Built: 2026-07-27 | Source commit: 5f287a1 -->

# PayResolve AI — Week 01 Report

## Included canonical sources

- `reports/week_01/week_01_summary.md`
- `reports/week_01/daily/2026-07-23.md`
- `reports/week_01/daily/2026-07-24.md`
- `reports/week_01/daily/2026-07-27.md`
- `reports/week_01/experiments/W1-001_banking77_data_audit.md`
- `reports/week_01/experiments/W1-002_lexical_baseline.md`
- `reports/week_01/experiments/W1-003_semantic_baseline.md`
- `reports/week_01/experiments/W1-004_final_evaluation.md`
- `reports/week_01/results/banking77_data_audit.md`

---

<!-- Source: reports/week_01/week_01_summary.md -->

# Week 01 Summary

## P0 objective
Full Banking77 + exactly two baselines + reproducible evaluation + error analysis.

## Status
`PASSED` — W1-001 through W1-004 complete; Week 2 not started

## Final benchmark

Both frozen candidates were refit on the same 10,003 non-test samples and evaluated
on the untouched 3,080-row official test.

| Model | Accuracy | Macro-F1 | Correct | Errors | Dimension | Repro-run total |
|---|---:|---:|---:|---:|---:|---:|
| TF-IDF unigram + LR | 0.878247 | 0.878362 | 2,705 | 375 | 2,320 | 4.259 s |
| frozen MiniLM + LR | 0.908117 | 0.908075 | 2,797 | 283 | 384 | 92.227 s |

Semantic minus lexical: accuracy `+0.029870`; macro-F1 `+0.029713`.

## Key evidence and decisions

- Authoritative PolyAI data remains pinned to commit `57ec275...` and protocol
  membership SHA-256 `baa3d31f...c902`.
- Evaluation protocol was preregistered before test access; both frozen candidates
  used identical final-fit scope and no test-driven tuning.
- Paired outcomes: 2,611 both correct, 94 lexical-only, 186 semantic-only, and
  189 both wrong.
- Semantic improved 49 class F1 values, regressed 21, and left 7 unchanged.
- Thirty deterministic error/disagreement cases were reviewed. Ambiguous label
  boundaries were most common; transaction-state and product-rail confusions remain.
- Both models were correct on all seven normalized-overlap rows. Exclusion changes
  each aggregate metric by less than 0.0003, so the recommendation is insensitive.
- Confidence distributions are diagnostic only; no calibration/threshold was fitted.
- Primary and independent fresh-cache reruns matched all stable artifacts.
- Frozen MiniLM semantic baseline is selected downstream; lexical is fallback.

## Runtime trade-off

Lexical is about 20× faster for the full measured CPU final-fit/evaluation and has
no encoder cache. Semantic requires ~183 MB local encoder cache and ~21 MB embedding
cache, but its broad ~2.97 percentage-point aggregate gain satisfies the
preregistered clear-gain rule. These are local CPU experiment timings, not
production latency claims.

## P0 exit criteria
- [x] W1-001 data audit and deterministic locked split.
- [x] W1-002 lexical baseline frozen without test tuning.
- [x] W1-003 semantic baseline frozen without test tuning.
- [x] W1-004 fair official-test evaluation of exactly two candidates.
- [x] Accuracy, macro-F1, all-class metrics, predictions, and confusions.
- [x] Paired, confidence, overlap, runtime, and bounded manual error analysis.
- [x] Reproducibility and public-safety evidence.
- [x] Downstream candidate selected and frozen.
- [x] Week 1 P0 gate passed.

## Limitations
- Seven normalized official-boundary overlaps are retained and disclosed.
- Some Banking77 queries are underspecified or appear inconsistent with fine-grained
  labels; hypotheses are not treated as proven annotation errors.
- No calibration, abstention, OOS/OOD, third model, or fine-tuning was performed.
- Semantic inference cost must be revisited when a real service latency target exists.

## Handoff
Week 1 is closed. Queue Week 2 only; do not implement it without separate user
authorization. Carry exact semantic revision/config as the selected intent model
and retain lexical unigram as the reproducible fallback.

---

<!-- Source: reports/week_01/daily/2026-07-23.md -->

# Daily Report — 2026-07-23

## 1. Goal

Complete `W1-001`, then execute separately authorized `W1-002`: lock the
authoritative Banking77 protocol and establish one reproducible lexical baseline
without touching the frozen official test.

## 2. Tasks

- `W1-001` — completed with reproducibility, integrity, split, and test evidence.
- `W1-002` — completed with validation-only evidence.
- `W1-003` / `W1-004` — not started.

## 3. Work completed

- Resolved authoritative PolyAI `master` to immutable commit
  `57ec275d8078af65b7731c2a98be812d844a6d6b`.
- Acquired only `categories.json`, `train.csv`, and `test.csv` from commit-pinned
  GitHub raw URLs into ignored `data/raw/`; no mirror or nested clone was used.
- Locked source SHA-256 checksums and the upstream CC-BY-4.0 license reference.
- Implemented a standard-library loader, source validation, integrity audit,
  stable sample IDs, hash-stratified validation split, artifact writer, and
  deterministic verification CLI.
- Preserved all 3,080 official test rows as frozen test. Derived 1,005 validation
  rows only from official train using per-label 10% rounded allocation, seed
  `20260723`, and SHA-256 ordering; retained 8,998 training rows.
- Audited null/empty/labels, exact duplicates, conflicting labels, class
  distribution, official-boundary overlap, and short queries.
- Found 7 case-folded/whitespace-normalized official train/test overlaps; all are
  label-consistent. Preserved the authoritative boundary and flagged this as a
  W1-004 evaluation limitation instead of mutating data or tuning on test.
- During W1-001, performed no model training or benchmark evaluation. Across the
  day, no W1-003, W1-004 frozen-test evaluation, P1, or Week 2 work was performed.

### W1-002 lexical baseline

- Installed CPython 3.11.9 at user scope because the machine initially exposed
  only 3.10/3.13, then created ignored `.venv-w1` and installed five exact pins.
- Implemented a config-driven TF-IDF + Logistic Regression validation CLI. Its
  data loader verifies source checksums and locked membership, reads only
  `categories.json` and `train.csv`, and has no test evaluation path.
- Compared only word unigrams against word uni+bigrams with every other setting
  fixed. Unigram was selected on validation macro-F1.
- Recorded validation accuracy 0.865672 and macro-F1 0.862649 for the selected
  unigram configuration. The bigram candidate recorded 0.857711 / 0.846269.
- Generated aligned predictions for all 1,005 validation IDs, 77-class metrics,
  directional confusion counts, version metadata, and a local portable fitted
  parameter artifact. No official-test prediction or metric was generated.
- Reviewed 20 validation errors. Frequent three-case confusions involved payment
  rail recognition and pending/reverted/failed transaction states.
- Replaced non-byte-stable joblib persistence with canonical JSON + deterministic
  gzip after proving joblib bytes changed across processes despite identical
  predictions and metrics.

## 4. Files changed

- `configs/data/banking77_w1_locked.json` — pinned source, checksums, license, and split config.
- `src/payresolve_ai/data/` and `scripts/data/banking77.py` — reusable implementation and CLI.
- `tests/test_banking77.py` — data/split/manifest regression coverage.
- `data/banking77_source_manifest.json` — trackable provenance.
- `data/banking77_split_manifest.json` — membership IDs, distributions, and hashes without raw text.
- `data/README.md`, `docs/DEVELOPMENT.md` — exact acquisition/audit/verify commands.
- `reports/week_01/experiments/W1-001_banking77_data_audit.md` — decision/audit note.
- `reports/week_01/results/banking77_data_audit.{json,md}` — actual evidence.
- `PROJECT_STATE.md`, `TASKS.md`, and `reports/week_01/week_01_summary.md` — project memory.
- `requirements/week1-lexical.txt`, `configs/models/banking77_lexical_w1.json` —
  pinned W1-002 environment and experiment contract.
- `src/payresolve_ai/baselines/`, `scripts/baselines/lexical.py` — lexical pipeline,
  validation-only loader, portable model persistence, and CLI.
- `tests/test_lexical_baseline.py` — scope, alignment, invalid-config, and
  reproducibility coverage.
- `reports/week_01/experiments/W1-002_lexical_baseline.md` and
  `reports/week_01/results/lexical_*` — actual W1-002 evidence.

## 5. Verification performed

Commands:

```powershell
git ls-remote https://github.com/PolyAI-LDN/task-specific-datasets.git refs/heads/master
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json acquire --refresh
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json audit-lock
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json verify
py -3.11 -m unittest discover -s tests -v
py -3.11 scripts/reporting/validate_project_docs.py
py -3.11 scripts/reporting/build_week_report.py --week 1 --format md
py -3.11 scripts/baselines/lexical.py --root . --config configs/models/banking77_lexical_w1.json --inspect-errors 20
```

Results:

- Tests: 12/12 passed on Python 3.11.9.
- Project/report/public-safety validation: passed.
- Two consecutive audit-lock runs were byte-identical across all four generated
  provenance/split/audit outputs (`match=True`).
- Deterministic `verify`: passed raw checksums and exact regenerated artifact bytes.
- Dataset/model metrics: none; W1-001 is data preparation only.
- W1-002 selected validation metrics: accuracy 0.865672; macro-F1 0.862649.
- Full suite after W1-002: 15/15 tests passed on Python 3.11.9.
- Two consecutive W1-002 runs were byte-identical for model parameters, metrics,
  per-class scores, predictions, confusions, and manifest.
- W1-002 evaluation scope was validation only (`test_evaluated=false`).

## 6. Problems / debugging

### Normalized official-boundary overlap

- Symptom: exact train/test overlap was 0, but case-folded/whitespace-normalized
  comparison found 7 shared queries.
- Root cause: official upstream contains case/whitespace variants on both sides of
  its train/test boundary.
- Resolution: do not remove, resplit, or tune using test. Preserve upstream and
  retain all 7 cases with labels/sample IDs as explicit evidence.
- Regression protection: a unit test verifies normalized overlaps are evidenced
  without silently removing them; W1-004 must interpret results with this slice.

### Non-deterministic joblib bytes

- Symptom: repeated runs produced identical predictions/metrics but different
  serialized joblib and manifest SHA-256 values.
- Root cause: object serialization ordering varied across independent processes.
- Resolution: persist complete fitted parameters as canonical JSON compressed by
  gzip with `mtime=0`; all six artifact hashes then matched across reruns.

## 7. Decisions / trade-offs

- Official test boundary takes precedence over random re-splitting.
- Hash ordering replaces library RNG so membership is stable across environments.
- Full membership IDs are committed without raw text so downstream tasks can
  verify the exact protocol while raw payloads remain ignored.
- Near-duplicate work stops at lightweight normalization; fuzzy deduplication
  would widen W1-001 without a demonstrated need.
- Lexical selection uses validation macro-F1 and only one controlled variable,
  word `ngram_range`; no broad sweep or third model was allowed.
- Single-thread numerical execution and a portable parameter format make the
  selected model artifact reproducible across independent local runs.

## 8. Evidence

- Source manifest: `data/banking77_source_manifest.json`.
- Locked membership: `data/banking77_split_manifest.json`.
- Audit JSON/Markdown: `reports/week_01/results/banking77_data_audit.*`.
- Detailed audit note: `reports/week_01/experiments/W1-001_banking77_data_audit.md`.
- Generated weekly aggregate: `reports/week_01/exports/week_01_report.md`.
- Combined membership SHA-256:
  `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`.
- Raw source files remain ignored and are not Git candidates.
- Commit/PR: pending; no stage, commit, push, or merge performed.
- W1-002 manifest: `reports/week_01/results/lexical_baseline_manifest.json`.
- Selected local model SHA-256:
  `4f564e227c5f61164d51710b1a86c6e8405fa0a793cf5b71b9842f0b40d5b021`.

## 9. Risks / blockers

- Seven label-consistent normalized train/test overlaps may make aggregate test
  results slightly optimistic; report the slice in W1-004.
- Exhaustive semantic annotation review was not performed; suspected ambiguity is
  handled through later confusion/error analysis.
- No blocker remains for W1-001 or W1-002. W1-003 requires separate review and
  authorization; the Week 1 P0 gate remains open.

## 10. Next step

- Stop. Queue `W1-003` without executing it; do not evaluate the frozen test
  before W1-004.

## Suggested commit message

`feat(baseline): add reproducible Banking77 lexical validation`

---

<!-- Source: reports/week_01/daily/2026-07-24.md -->

# Daily Report — 2026-07-24

## 1. Goal

Complete `DOC-001`: create reader-friendly Markdown views of the authoritative
`docs/MASTER_PRD.md` without changing project requirements or opening W1-003.

## 2. Scope and acceptance criteria

- Classification: P0 documentation support; it does not change the Week 1 gate.
- Put all reader copies under `tai_lieu/`.
- Cover numbered master sections 0–19 exactly once, with no missing or duplicate
  section assignment.
- Keep `docs/MASTER_PRD.md` unchanged and clearly identified as the sole source of
  truth.
- Provide a reproducible generation/check command.

## 3. Work completed

- Added `scripts/reporting/split_master_prd.py` to parse numbered sections from
  the master and generate eight topic files plus a reader index.
- Generated `Brief.md`, `PRD.md`, `Data_Strategy.md`, `Evaluation_Plan.md`,
  `System_Architecture.md`, `Internship_Plan.md`, `Delivery_and_Success.md`, and
  `References.md` under `tai_lieu/`.
- Added an authority notice to every generated topic file and a section-to-file
  map in `tai_lieu/README.md`.
- Made check mode detect missing, stale, modified, or unexpected Markdown files.
- Updated the repository validator narrowly: `tai_lieu/PRD.md` is accepted only
  when it is the byte-current generated reader copy; any manual modification or
  additional PRD file still triggers the competing-PRD guard.
- Added a regression test proving a current generated PRD is accepted and a
  manually modified reader PRD is rejected.
- Did not modify `docs/MASTER_PRD.md`, model code, data, split membership,
  benchmark evidence, or the frozen test protocol.

## 4. Verification performed

Commands:

```powershell
py -3.11 scripts/reporting/split_master_prd.py --root .
py -3.11 scripts/reporting/split_master_prd.py --root . --check
py -3.11 scripts/reporting/validate_project_docs.py
py -3.11 -m unittest discover -s tests -v
git diff -- docs/MASTER_PRD.md
```

Results:

- Generated 9 Markdown files under `tai_lieu/`.
- Check passed: master sections 0–19 are complete, current, and assigned exactly
  once.
- Initial project validation correctly flagged `tai_lieu/PRD.md` under the old
  blanket competing-PRD rule. After adding the generated-copy invariant and its
  regression test, project validation passed.
- Reporting regression tests: 7/7 passed.
- Full unit suite: 16/16 passed on Python 3.11.
- One full-suite retry initially failed during Python startup with `MemoryError`
  after a parallel test process had not returned a final result. No assertion ran
  in that attempt; after confirming no Python process remained, the relevant
  suite and then the full suite passed sequentially.
- `git diff -- docs/MASTER_PRD.md` produced no output; the master is unchanged.

## 5. Decisions and risks

- Generated topic files are navigation/readability copies only. Requirement
  changes must be made in `docs/MASTER_PRD.md` and then regenerated.
- Sections are grouped by topic, so their order across files differs from the
  original master; section text itself is copied without manual rewriting.
- W1-003 remains queued and requires separate user authorization.

## 6. Project memory updated

- `PROJECT_STATE.md` records the completed documentation support task and check.
- `TASKS.md` records `DOC-001` as done.
- The Week 1 P0 model/evaluation gate remains in progress and unchanged.

## Suggested commit message

`docs(prd): add reader-friendly generated master views`

---

<!-- Source: reports/week_01/daily/2026-07-27.md -->

# Daily Report — 2026-07-27

## 1. Goal
Complete W1-003 and the separately authorized W1-004 final locked-test evaluation
without model retuning, a third model, P1, or Week 2 implementation.

## 2. Tasks
- `W1-003` — completed and committed as `5f287a1`.
- `W1-004` — completed; Week 1 P0 gate passed.

## 3. Work completed
- Completed and verified the frozen semantic validation baseline.
- Verified clean Git/pre-test state and all W1-001/W1-002/W1-003 hashes.
- Preregistered W1-004 final-fit, metrics, analysis, decision, rerun, and stop rules.
- Refit both frozen candidates on the same 10,003 non-test samples.
- Ran one primary and one identical reproducibility evaluation on official test.
- Produced aligned metrics, predictions, per-class, confusion, paired, confidence,
  overlap-sensitivity, runtime, model-selection, and final manifest evidence.
- Reviewed and annotated a deterministic 30-row error/disagreement sample.
- Selected frozen MiniLM semantic baseline; retained lexical as fallback.

## 4. Files changed
- `configs/evaluation/banking77_w1_final.json` — preregistered evaluation contract.
- `src/payresolve_ai/evaluation/` and `scripts/evaluation/` — final evaluation pipeline/CLI.
- `tests/test_week1_final_evaluation.py` — frozen-contract and alignment regressions.
- `reports/week_01/results/intent_benchmark.*`, `*_test_*`, and `week1_*` — evidence.
- `reports/week_01/experiments/W1-004_final_evaluation.md` — final analysis/decision.
- Project state, task board, Week 1 summary, development workflow, and validator.

## 5. Verification performed

```powershell
.venv-semantic\Scripts\python.exe scripts\evaluation\week1_final.py --root . --config configs\evaluation\banking77_w1_final.json verify-pretest
.venv-semantic\Scripts\python.exe scripts\evaluation\week1_final.py --root . --config configs\evaluation\banking77_w1_final.json run --run-label primary
.venv-semantic\Scripts\python.exe scripts\evaluation\week1_final.py --root . --config configs\evaluation\banking77_w1_final.json run --run-label reproducibility_rerun
.venv-semantic\Scripts\python.exe scripts\evaluation\week1_final.py --root . --config configs\evaluation\banking77_w1_final.json finalize
.venv-semantic\Scripts\python.exe scripts\evaluation\week1_final.py --root . --config configs\evaluation\banking77_w1_final.json verify-results
.venv-semantic\Scripts\python.exe -m unittest discover -s tests -v
```

Results:
- Lexical test accuracy/macro-F1: `0.878247 / 0.878362`; 2,705 correct.
- Semantic test accuracy/macro-F1: `0.908117 / 0.908075`; 2,797 correct.
- Semantic deltas: accuracy `+0.029870`; macro-F1 `+0.029713`.
- Paired: 2,611 both correct; 94 lexical-only; 186 semantic-only; 189 both wrong.
- Primary/repro stable artifacts matched byte-for-byte.
- W1-004 result validator: PASS; Week 1 P0 gate: PASS.
- Isolated W1-004 tests: 7/7 PASS; isolated lexical: 3/3 PASS;
  isolated semantic: 4/4 PASS; full suite: 27/27 PASS.
- Locked Banking77 artifact verification and semantic contract verification: PASS.

## 6. Problems / debugging

### Preregistration Git SHA typo
- Symptom: recovery check found the preregistered full SHA had a correct short
  prefix but an incorrect suffix.
- Root cause: the full value was typed rather than read from `git rev-parse HEAD`.
- Fix: replaced it with `5f287a18a50ec073f961290962de003e1f4e38bc` before test access.
- Protection: `verify-pretest` now must match full Git HEAD; no prior test artifact existed.

### Git provenance fixture
- W1-003's temp-root Git assumption was fixed and retained as a regression test.

## 7. Decisions / trade-offs
- Final-fit protocol: identical 10,003-sample scope for both frozen candidates.
- Selected semantic MiniLM because the preregistered clear-gain rule passed.
- Lexical remains a much faster and smaller fallback.
- Confidence remains diagnostic and uncalibrated; no P1 threshold work was opened.

## 8. Evidence
- Canonical benchmark: `reports/week_01/results/intent_benchmark.json`.
- Full manifest: `reports/week_01/results/week1_final_manifest.json`.
- Analysis: `reports/week_01/experiments/W1-004_final_evaluation.md`.
- Raw data, weights, embeddings, and fitted models remain ignored.
- W1-004 commit/PR: pending; no stage, commit, push, or merge performed.

## 9. Risks / blockers
- Seven normalized official-boundary overlaps remain a disclosed limitation.
- Some errors reflect ambiguous or potentially inconsistent taxonomy boundaries.
- Semantic CPU/cache cost is higher; measured runtime is not production latency.
- No Week 2 blocker is claimed, but Week 2 needs separate authorization.

## 10. Next step
Stop for review. Week 2 is queued and not started.

## Suggested commit message
`feat(evaluation): complete Banking77 Week 1 benchmark`

---

<!-- Source: reports/week_01/experiments/W1-001_banking77_data_audit.md -->

# W1-001 — Banking77 Data Audit and Locked Split

## Objective

Create the single reproducible Banking77 data protocol that W1-002 and W1-003
must share, while preserving the mentor-provided official test boundary.

## Authoritative source and provenance

- Source: `https://github.com/PolyAI-LDN/task-specific-datasets/tree/master/banking_data`
- Repository: `https://github.com/PolyAI-LDN/task-specific-datasets.git`
- Resolved revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`
- Revision resolution: `git ls-remote ... refs/heads/master`; all downloads then
  used immutable raw URLs containing that SHA.
- License at pinned repository revision: CC-BY-4.0 (`LICENSE`).
- Acquired files only: `categories.json`, `train.csv`, `test.csv`.
- Transport: direct authoritative GitHub raw URLs; no mirror and no nested clone.

| Source file | Bytes | SHA-256 |
|---|---:|---|
| `categories.json` | 2,036 | `53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63` |
| `train.csv` | 839,073 | `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b` |
| `test.csv` | 239,961 | `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d` |

Raw files are stored under the revision-specific ignored `data/raw/banking77/`
path and are not Git candidates.

## Actual audit findings

- Samples: 13,083 total; 10,003 official train; 3,080 official test.
- Taxonomy: 77 unique intents; all appear in both official splits.
- Official-train class count range: 35–187.
- Official test is balanced at 40 examples for each of 77 intents.
- Missing/null fields: 0; empty text: 0; empty labels: 0; invalid labels: 0.
- Exact-query duplicate groups: 0.
- Exact query-label duplicate groups: 0.
- Exact same-query conflicting-label groups: 0.
- Exact official train/test query overlap: 0.
- Case-folded/whitespace-normalized official train/test overlap: 7; all 7 are
  label-consistent and 0 are label-conflicting. The source boundary is preserved;
  these cases are flagged as a potential optimistic-evaluation limitation for
  W1-004 rather than removed or used to tune a model.
- Unusually short queries: 0 with at most 1 token, 9 with at most 2 tokens, and 49
  with at most 3 tokens. Stable sample IDs and representative cases are retained
  in the JSON/Markdown evidence.
- Near-duplicate scope was intentionally lightweight: case-folded and whitespace-
  normalized exact comparison only. No fuzzy-dedup research or data mutation was
  performed.
- Automated label integrity found no invalid/missing/conflicting label. Exhaustive
  semantic annotation review is outside W1-001; model confusions and suspected
  annotation ambiguity are deferred to W1-004 error analysis.

## Locked split protocol

- `test`: unchanged official `test.csv`; frozen and prohibited for tuning.
- `train`/`validation`: derived only from official `train.csv`.
- Validation allocation: per-label rounded 10%, with at least one validation and
  one remaining training example per label.
- Seed: `20260723`.
- Ordering: SHA-256 of `seed + NUL + stable_sample_id`; no library RNG dependency.
- Stable sample ID includes source filename, source row, text, and label.

| Locked split | Samples | Classes | Per-class range | Membership SHA-256 |
|---|---:|---:|---:|---|
| Train | 8,998 | 77 | 31–168 | `2a7f9d939d2277acd4686beb0d0cd65de69de2b0cf14654f55c24d275a611d98` |
| Validation | 1,005 | 77 | 4–19 | `2cc9823902450a9a9b7cf8cb6e48042799d81c59a3f1beb274495a67d238fe40` |
| Frozen test | 3,080 | 77 | 40 | `e645d236834def2e60f383aa9130ade0885ef50db459dd50c03fbb48ccca8a25` |

Combined membership SHA-256:
`baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`.

## Reproducibility evidence

Two consecutive `audit-lock` runs produced byte-identical artifacts. The first
recorded before/after comparison returned `match=True` for all four outputs.
Current deterministic artifact hashes:

| Artifact | SHA-256 |
|---|---|
| `data/banking77_source_manifest.json` | `9e9ffef74113671ce17ad7ace6490d757e13b4321df8d3e44ad6be10863565aa` |
| `data/banking77_split_manifest.json` | `dfb2c0f54eda2796614032708c630cecef18d066cf050e02b3394e812896fffd` |
| `reports/week_01/results/banking77_data_audit.json` | `695ecc0874cf0dd7375b8456079ddef8d4fe439f366bd95fe7b74f7c8c2e2ead` |
| `reports/week_01/results/banking77_data_audit.md` | `7a73e24d5c345503311c12b0bddc3089e7f0c768a40961f8f3fbf2c6641499c1` |

The `verify` command independently recomputed raw checksums, audit content, split
membership, and artifact bytes and passed.

## Commands

```powershell
git ls-remote https://github.com/PolyAI-LDN/task-specific-datasets.git refs/heads/master
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json acquire --refresh
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json audit-lock
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json verify
py -3.11 -m unittest discover -s tests -v
```

## Decision

Accept `banking77_w1_v1` as the only W1-002/W1-003 data protocol. Downstream code
must verify the manifest before use, must not resplit official data, and must use
validation—not frozen test—for selection/tuning. W1-001 makes no model-quality
claim and starts no baseline.

---

<!-- Source: reports/week_01/experiments/W1-002_lexical_baseline.md -->

# W1-002 — Controlled Lexical Baseline

## Objective and scope

Establish one simple lexical reference using TF-IDF + Logistic Regression on the
locked `banking77_w1_v1` development protocol. This task performs model selection
only on validation. It does not load, predict, or evaluate the 3,080-row frozen
official test set; that single controlled evaluation is reserved for W1-004.

## Inputs and invariants

- Authoritative source revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`.
- Locked membership: 8,998 train / 1,005 validation / 3,080 frozen test.
- Combined membership SHA-256:
  `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`.
- Runtime: CPython 3.11.9 with exact pins in
  `requirements/week1-lexical.txt`.
- Classifier, seed, solver, and all settings except `ngram_range` were held fixed.
- Selection metric was validation macro-F1; accuracy and candidate ID were fixed
  tie-breakers.

## Controlled candidates

| Candidate | Word n-grams | Features | Validation accuracy | Validation macro-F1 |
|---|---:|---:|---:|---:|
| `word_unigram` | 1–1 | 2,237 | 0.865672 | 0.862649 |
| `word_unigram_bigram` | 1–2 | 22,225 | 0.857711 | 0.846269 |

Both candidates used lowercase text, `min_df=1`, sublinear TF, LogisticRegression
with `C=1.0`, `solver=lbfgs`, `max_iter=1000`, seed `20260723`, and a fixed
single-thread numerical execution policy.

## Decision

Freeze `word_unigram` for the later W1-004 comparison. It improved validation
macro-F1 by 0.016381 and accuracy by 0.007960 while using about one tenth as many
features. No additional lexical sweep or third model was opened.

## Minimal validation error inspection

The selected model made 135 errors among 1,005 validation examples. The most
frequent directional confusion pairs (three cases each) were:

- `direct_debit_payment_not_recognised` → `card_payment_not_recognised`;
- `pending_top_up` → `top_up_failed`;
- `reverted_card_payment?` → `request_refund`;
- `top_up_reverted` → `top_up_failed`.

Representative stable sample IDs reviewed included
`10c97cc5...216d1d5` (unrecognized payment without a strong payment-rail cue),
`10414657...b540110` (top-up “didn't finish”), and
`5450a431...2ed638` (transfer timing vs pending transfer). The evidence supports
a lexical limitation: neighboring intents often share transaction nouns while
the decisive distinction is event state, rail, or temporal semantics. This is a
W1-002 observation only, not the final W1-004 taxonomy or gate decision.

Lowest selected per-class F1 values were `card_acceptance` (0.545455),
`card_not_working` (0.571429), `topping_up_by_card` (0.666667), and
`virtual_card_not_working` (0.666667). Per-class support is retained in the CSV;
small validation support means these values are diagnostic, not final test claims.

## Reproducibility and artifact decision

Exact command:

```powershell
py -3.11 scripts/baselines/lexical.py --root . --config configs/models/banking77_lexical_w1.json --inspect-errors 20
```

Two consecutive independent runs produced byte-identical metrics, predictions,
per-class metrics, confusions, portable model parameters, and manifest. The model
uses canonical JSON + deterministic gzip rather than joblib serialization because
joblib bytes varied across processes despite identical predictions/metrics. The
portable artifact records vocabulary, IDF, class order, coefficients, and
intercepts and remains ignored under `artifacts/`; its SHA-256 is
`4f564e227c5f61164d51710b1a86c6e8405fa0a793cf5b71b9842f0b40d5b021`.

## Evidence

- Config: `configs/models/banking77_lexical_w1.json`.
- Metrics: `reports/week_01/results/lexical_validation_metrics.json`.
- Per-class metrics: `reports/week_01/results/lexical_validation_per_class.csv`.
- Predictions: `reports/week_01/results/lexical_validation_predictions.csv`.
- Confusion counts: `reports/week_01/results/lexical_validation_confusions.csv`.
- Version/hashes: `reports/week_01/results/lexical_baseline_manifest.json`.
- Tests: 15/15 passed after adding W1-002 coverage.

## Limitations and next boundary

- These are validation results, not official test results.
- The two-candidate comparison isolates only word bigrams; it is not a broad
  hyperparameter search.
- W1-003 has not started. W1-004 must later evaluate exactly the two frozen
  baselines once on the untouched official test and perform the final analysis.

---

<!-- Source: reports/week_01/experiments/W1-003_semantic_baseline.md -->

# W1-003 — Frozen Semantic Representation Baseline

## Objective and hypothesis

Test whether one pretrained dense semantic representation improves fine-grained
Banking77 intent classification over the frozen lexical reference, especially
when surface vocabulary is shared but transaction state, payment rail, or
operational meaning differs.

This is a controlled representation comparison:

```text
W1-002: TF-IDF word unigrams → Logistic Regression
W1-003: frozen all-MiniLM-L6-v2 embeddings → Logistic Regression
```

The downstream classifier remains `C=1.0`, `lbfgs`, `max_iter=1000`, seed
`20260723`, and one numerical thread. No model/config search was performed.

## Frozen contracts

- Data protocol: `banking77_w1_v1`.
- Train/validation/frozen test: 8,998 / 1,005 / 3,080.
- Membership SHA-256:
  `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`.
- Lexical config SHA-256:
  `f99955a401063fa849d93af2dec3639e8e3aaa3f8a99d3029b0ce01edb02b64d`.
- Frozen test encoded/evaluated: no/no.

The semantic loader reuses W1-002's locked train/validation loader and metric
functions. It does not reference a test example or create a test cache.

## Encoder provenance and configuration

- Model ID: `sentence-transformers/all-MiniLM-L6-v2`.
- Exact Hugging Face revision:
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- License recorded from upstream metadata: Apache-2.0.
- Encoder frozen: yes; all parameters have `requires_grad=false` and eval mode.
- Pooling: mean.
- Output dimension: 384.
- Sentence Transformer/tokenizer maximum sequence length: 256.
- Embedding normalization: L2 normalization enabled, predeclared before run.
- Batch size: 64.
- Device: CPU; CUDA unavailable.
- Remote code: not trusted/executed.

The local snapshot contained 11 required files totaling 91,578,415 bytes. The
90,868,376-byte `model.safetensors` SHA-256 is
`53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`.
Weights remain under ignored `artifacts/`; only provenance and checksums are
trackable.

## Executions

1. Contract tests with a deterministic fake encoder.
2. Realistic smoke test: 16 train / 4 validation rows across four classes;
   embeddings `(16,384)` and `(4,384)`; four predictions; no metric used as final
   evidence.
3. One full primary run with the predeclared configuration.
4. One independent full refresh rerun of the same configuration.
5. Cache verification and limited validation-only error inspection.

No alternative encoder, normalization, pooling, `C`, or classifier was tried.

## Validation results

| Baseline | Accuracy | Macro-F1 | Correct | Errors |
|---|---:|---:|---:|---:|
| Frozen lexical unigram | 0.865672 | 0.862649 | 870 | 135 |
| Frozen semantic encoder | 0.900498 | 0.898020 | 905 | 100 |
| Semantic − lexical | +0.034826 | +0.035371 | +35 | −35 |

These are validation results only. They do not establish a frozen-test winner.

## Per-class and confusion findings

Using strict F1 change relative to lexical:

- 43 classes improved;
- 14 regressed;
- 20 were unchanged;
- 14 improved by at least 0.10 F1;
- one regressed by at least 0.10 F1 (`cancel_transfer`, −0.125).

Largest improvements included `virtual_card_not_working` (+0.1905, support 4),
`top_up_by_card_charge` (+0.1739, support 11),
`declined_cash_withdrawal` (+0.1606, support 17), and
`balance_not_updated_after_bank_transfer` (+0.1444, support 17). Small support,
especially four rows, makes these diagnostic rather than final claims.

Largest regressions included `cancel_transfer` (−0.125),
`wrong_amount_of_cash_received` (−0.100 within floating representation),
`card_about_to_expire` (−0.080), and `compromised_card` (−0.0743).

For the four W1-002 focus confusions:

| True → predicted | Lexical | Semantic | Change |
|---|---:|---:|---:|
| direct debit unrecognized → card payment unrecognized | 3 | 2 | −1 |
| pending top-up → top-up failed | 3 | 2 | −1 |
| reverted card payment → request refund | 3 | 0 | −3 |
| top-up reverted → top-up failed | 3 | 3 | 0 |

Semantic representation reduced three focus pairs but did not solve reverted vs
failed top-up. It also created new two-case patterns such as
`cancel_transfer → terminate_account`, `card_about_to_expire → order_physical_card`,
and `reverted_card_payment? → Refund_not_showing_up`. These examples suggest the
encoder can improve operational semantics overall while still collapsing intents
whose short wording omits the decisive event/state cue.

## Runtime and cache evidence

Primary CPU run:

- Model load: 8.79 seconds.
- Train encoding: 58.89 seconds for 8,998 rows.
- Validation encoding: 8.24 seconds for 1,005 rows.
- Classifier fit: 2.65 seconds.
- Validation prediction: 0.024 seconds.
- Total experiment: 79.31 seconds.
- Embedding cache: 16,086,001 bytes.
- Hugging Face cache: 183,156,831 bytes; required snapshot footprint was
  91,578,415 bytes, with cache metadata/blob duplication accounting for the
  larger on-disk cache directory.

These are local experiment timings, not production latency. Compared with the
2,237-dimensional sparse lexical representation, semantic uses 384 dense values
per query but adds pretrained model loading/encoding complexity.

## Cache and reproducibility

Cache key:
`c7e89e194c319cb4217a91302a663058773f494d5bc51e8261a8900832d09302`.

- Train embedding shape/hash: `(8998,384)`,
  `ffa3572d9c24940fe72466ab1ce42599e88ff7cdf9e897c32509bbb5249be0b6`.
- Validation embedding shape/hash: `(1005,384)`,
  `c2c717f087f0b6896ce4d68e2144f58c60b9f558e1985b19568c0ee2b7422048`.
- Train/validation sample-ID hashes were independently verified.
- Both primary and reproducibility runs forced fresh encoding (`cache_hit=false`).
- Eight stable artifacts were byte-identical across independent refresh runs:
  classifier parameters, metrics, per-class metrics, predictions, confusions,
  embedding manifest, model provenance, and lexical comparison.
- Runtime and overall manifest bytes intentionally differ because measured timing
  and run-label evidence differ; this is not numerical nondeterminism.

## Debugging evidence

The first full test run exposed an integration-fixture bug: Git provenance assumed
every supplied repository root contained `.git`. The full project run was valid,
but the isolated temp-root test failed. The helper now records
`{"available": false}` outside Git and continues to record HEAD/dirty state in the
real repository. The previously failing integration test is the regression guard.

Hugging Face also reported that optional Xet acceleration was absent and used its
regular HTTP fallback. No new dependency was added because correctness and exact
revision acquisition succeeded without it.

Pre-commit verification on 2026-07-27 ran the semantic test module in isolation
with `.venv-semantic` before the full suite. Direct imports resolved from
`src/payresolve_ai`; the isolated module passed 4/4 tests and the same interpreter
then passed the full 20/20 tests. This confirms the semantic tests do not depend on
another test mutating `sys.path` first.

## Decision and boundary

Freeze this semantic configuration for W1-004. Validation supports H1, but the
official test performance remains unknown. Do not retune either baseline, start a
third model, or perform the final cross-model/frozen-test decision within W1-003.

## Evidence

- Config: `configs/models/banking77_semantic_w1.json`.
- Dependency lock: `requirements/week1-semantic.txt`.
- Model provenance: `reports/week_01/results/semantic_model_provenance.json`.
- Embedding manifest: `reports/week_01/results/semantic_embedding_manifest.json`.
- Metrics/predictions/per-class/confusions: `reports/week_01/results/semantic_validation_*`.
- Lexical comparison: `reports/week_01/results/semantic_lexical_validation_comparison.json`.
- Runtime: `reports/week_01/results/semantic_runtime.json`.
- Frozen result manifest: `reports/week_01/results/semantic_baseline_manifest.json`.

---

<!-- Source: reports/week_01/experiments/W1-004_final_evaluation.md -->

# W1-004 — Final Locked Test Evaluation and Week 1 Gate

## Verdict

`PASS`. Both frozen baselines were refit once per run on all 10,003 official
training samples and evaluated on the 3,080-row official test under the
preregistered protocol. Semantic MiniLM is selected for downstream use; the
lexical unigram model remains the fallback. No test-driven tuning occurred.

## Pre-test gate and preregistration

- Git HEAD and `origin/main`: `5f287a18a50ec073f961290962de003e1f4e38bc`.
- W1-001/W1-002/W1-003 commits and frozen manifests verified.
- Protocol: `banking77_w1_v1`; membership SHA-256 `baa3d31f...c902`.
- Prior state: `test_encoded=false`, `test_evaluated=false`; no prior test artifacts.
- Evaluation config created before test access with SHA-256
  `a6ac09654884528aa6ccabf784a349304eddecb3ccb0add680000ad4f6272a40`.
- An initially typed full Git SHA was corrected before test access. The gate caught
  the mismatch; no test artifact existed and no score had been observed.

The preregistered final-fit protocol was identical for both candidates:

```text
locked train 8,998 + locked validation 1,005
→ 10,003 samples ordered by stable sample ID
→ refit each frozen configuration once
→ evaluate on 3,080 official-test samples ordered by stable sample ID
```

## Official benchmark

| Model | Representation | Accuracy | Macro-F1 | Correct | Errors | Dimension | Repro-run total |
|---|---|---:|---:|---:|---:|---:|---:|
| Lexical | TF-IDF word unigram | 0.878247 | 0.878362 | 2,705 | 375 | 2,320 | 4.259 s |
| Semantic | normalized frozen MiniLM | 0.908117 | 0.908075 | 2,797 | 283 | 384 | 92.227 s |

Semantic minus lexical: accuracy `+0.029870`; macro-F1 `+0.029713`.

Validation-to-test changes were positive for both models:

- lexical: accuracy `+0.012575`, macro-F1 `+0.015713`;
- semantic: accuracy `+0.007619`, macro-F1 `+0.010054`.

These values are not used for retuning.

## Paired outcomes

| Outcome | Count |
|---|---:|
| Both correct | 2,611 |
| Lexical correct / semantic wrong | 94 |
| Lexical wrong / semantic correct | 186 |
| Both wrong | 189 |

Semantic corrected 186 lexical errors while introducing 94 regressions, a net
gain of 92 correct predictions. The gain is broad: semantic F1 improved for 49
intents, regressed for 21, and was unchanged for 7. No semantic class regression
reached the preregistered absolute F1 threshold of 0.20.

Largest F1 improvements included `virtual_card_not_working` (+0.244821),
`card_not_working` (+0.162494), `why_verify_identity` (+0.153333), and
`verify_my_identity` (+0.149498). Largest regressions included
`declined_transfer` (-0.092515), `direct_debit_payment_not_recognised`
(-0.049787), `beneficiary_not_allowed` (-0.048583), and
`reverted_card_payment?` (-0.047414).

Validation findings did not all persist: `cancel_transfer` improved by 0.025610
on test; `top_up_reverted` improved by 0.082621; `pending_top_up` regressed by
0.032843; `request_refund` improved by 0.062657; and
`reverted_card_payment?` regressed by 0.047414.

## Confusions and bounded manual review

Semantic reduced several prominent directional confusions:

- `why_verify_identity → verify_my_identity`: 9 → 3;
- `virtual_card_not_working → get_disposable_virtual_card`: 8 → 1;
- `request_refund → Refund_not_showing_up`: 5 → 0;
- `top_up_reverted → top_up_failed`: 5 → 2.

It worsened `declined_transfer → declined_card_payment` from 2 → 6 and retained
fine-grained boundaries around transfer timing, direct debit/card recognition,
disposable cards, and transaction states.

The deterministic 30-row review contains semantic fixes, lexical-only correct
cases, both-wrong cases, high-confidence errors, low-margin errors, and short
queries. Taxonomy counts were T1=1, T2=5, T3=4, T4=3, T5=10, T6=2, T7=5.
Root-cause statements are hypotheses. The most common reviewed issue was ambiguous
or underspecified label boundaries, followed by transaction-state and product-rail
confusion. Five cases warrant potential annotation/taxonomy review; they are not
silently relabeled.

## Confidence diagnostics

Probabilities are diagnostic only and are not assumed calibrated.

- Lexical mean max probability: correct `0.5473`, incorrect `0.2374`.
- Semantic mean max probability: correct `0.6807`, incorrect `0.3422`.
- Lexical mean top-1/top-2 margin: correct `0.4769`, incorrect `0.1092`.
- Semantic mean top-1/top-2 margin: correct `0.5978`, incorrect `0.1694`.

Correct and incorrect distributions separate directionally, but confidently wrong
examples remain. No threshold, calibration, abstention, or OOS policy was fitted.

## Normalized-overlap sensitivity

Both models correctly classified all seven W1-001 normalized-overlap test rows.
Excluding only those evidenced rows yields 3,073 samples:

| Model | Accuracy excluding overlap | Macro-F1 excluding overlap | Accuracy change | Macro-F1 change |
|---|---:|---:|---:|---:|
| Lexical | 0.877969 | 0.878073 | -0.000277 | -0.000289 |
| Semantic | 0.907908 | 0.907874 | -0.000209 | -0.000201 |

The semantic recommendation does not materially depend on these seven rows. The
canonical benchmark remains the unmodified 3,080-row official test.

## Runtime and complexity

Primary/repro total evaluation times were 108.906/97.536 seconds. Per-model totals:

- lexical: 4.587/4.259 seconds; 2,320 features; portable model 1,666,588 bytes;
- semantic: 103.186/92.227 seconds; 384 dimensions; portable classifier 284,058
  bytes; local encoder cache 183,156,831 bytes; embedding cache 21,038,649 bytes.

Semantic is materially slower and requires model/cache storage, but its ~2.97
percentage-point aggregate gain and broad class improvements justify the added
complexity for this research prototype. These CPU measurements are not production
latency claims.

## Reproducibility and decision

Primary and independent fresh-cache reruns produced byte-identical classifier
parameters, predictions, metrics, per-class scores, confusions, paired rows,
confidence analysis, overlap analysis, and manual-review candidate selection.
Runtime-bearing benchmark/runtime artifacts differ as expected.

The preregistered `semantic_clear_gain` branch applies: macro-F1 improved by more
than 0.01, accuracy did not decrease, results reproduced, and there was no
per-class regression of at least 0.20. Selected candidate:

`semantic_all_minilm_l6_v2` using config SHA-256 `de4ebff8...7b50b`.

Fallback: `lexical_word_unigram`. Both remain frozen; no third model is opened.

## Week 1 P0 gate

`PASS`: W1-001 through W1-004 are complete; both frozen candidates were evaluated
fairly; required artifacts, error analysis, overlap limitation, recommendation,
tests, reproducibility, and public-safety evidence are present. Week 2 is queued
but was not started by this task.

Final verification: isolated W1-004 7/7, lexical 3/3, semantic 4/4, and full
repository suite 27/27 passed under the locked semantic environment. Banking77
artifact verification, semantic contract verification, and W1-004 result
verification also passed.

---

<!-- Source: reports/week_01/results/banking77_data_audit.md -->

# Banking77 Data Audit — W1-001

- Protocol: `banking77_w1_v1`
- Authoritative upstream revision: `57ec275d8078af65b7731c2a98be812d844a6d6b`
- Official `test.csv` is frozen and excluded from tuning.

## Source checksums

- `categories.json`: `53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63`
- `train.csv`: `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b`
- `test.csv`: `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d`

## Actual sample and label counts

- Official train: 10003
- Official test: 3080
- Total: 13083
- Intents: 77
- Official-train class range: 35–187
- Official-test class range: 40–40
- Locked-train class range: 31–168
- Validation class range: 4–19

## Integrity findings

- Empty text rows: 0
- Empty label rows: 0
- Invalid-label rows: 0
- Exact-query duplicate groups: 0
- Exact query-label duplicate groups: 0
- Conflicting-label query groups: 0
- Official train/test exact overlap: 0
- Official train/test case+whitespace-normalized overlap: 7 (7 label-consistent, 0 label-conflicting)
- Decision: preserve the authoritative official boundary and flag the 7 normalized overlaps as an evaluation limitation; do not remove or tune on test data.

### Normalized official train/test overlap cases

| Normalized query | Train label/text | Test label/text |
|---|---|---|
| at which atms can i use this card? | atm_support:  At which ATMs can I use this card? | atm_support: At which ATMs can I use this card? |
| how do i unblock my pin? | pin_blocked:  How do I unblock my PIN? | pin_blocked: How do I unblock my PIN? |
| i don't live in the uk. can i still get a card? | country_support: I don't live in the UK. Can I still get a card? | country_support: I don't live in the UK.  Can I still get a card? |
| there are a few transaction that i don't recognize, i think someone managed to get my card details and use it. | compromised_card: There are a few transaction that I don't recognize, I think someone managed to get my card details and use it.  | compromised_card: There are a few transaction that I don't recognize, I think someone managed to get my card details and use it. |
| what businesses accept this card? | card_acceptance: What businesses accept this card? | card_acceptance:   What businesses accept this card? |
| where can i use my card? | card_acceptance:  Where can I use my card? | card_acceptance: Where can I use my card? |
| which cash machines will allow me to change my pin? | change_pin:  Which cash machines will allow me to change my PIN? | change_pin: Which cash machines will allow me to change my PIN? |

## Unusually short queries

- Up to 1 token: 0
- Up to 2 tokens: 9
- Up to 3 tokens: 49

| Tokens | Label | Text |
|---:|---|---|
| 2 | `country_support` | Supported countries |
| 2 | `pending_transfer` | Pending transfer? |
| 2 | `cancel_transfer` | Cancel Transaction |
| 2 | `passcode_forgotten` | Lost password |
| 2 | `passcode_forgotten` | passcode retrieval |
| 2 | `exchange_via_app` | Change currency |
| 2 | `declined_transfer` | Transfer declined. |
| 2 | `pending_card_payment` | pending transaction? |
| 2 | `transfer_not_received_by_recipient` | transaction failed? |
| 3 | `declined_card_payment` | Card payment declined? |

## Locked protocol

- Strategy: `official_test_plus_hash_stratified_validation`
- Seed: `20260723`
- Train: 8998
- Validation: 1005
- Locked test: 3080
- Combined membership SHA-256: `baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902`

Detailed class distributions, short-query samples, membership IDs, and all counts are in the JSON artifacts.
