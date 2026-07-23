<!-- GENERATED FILE: edit canonical sources, not this aggregate. -->
<!-- Built: 2026-07-23 | Source commit: 8e321d6 -->

# PayResolve AI — Week 01 Report

## Included canonical sources

- `reports/week_01/week_01_summary.md`
- `reports/week_01/daily/2026-07-23.md`
- `reports/week_01/experiments/W1-001_banking77_data_audit.md`
- `reports/week_01/results/banking77_data_audit.md`

---

<!-- Source: reports/week_01/week_01_summary.md -->

# Week 01 Summary

## P0 objective
Full Banking77 + 2 baselines + reproducible evaluation + error analysis.

## Status
IN PROGRESS — W1-001 complete; W1-002/W1-003/W1-004 not started

## Deliverables completed
- W1-001 authoritative Banking77 acquisition/provenance contract.
- Deterministic official-train → train/validation membership with frozen official test.
- Data integrity/class-distribution/leakage/short-query audit.
- Reproducibility CLI, manifest verification, and regression tests.

## Key evidence
| Claim | Evidence | Result | Decision |
|---|---|---|---|
| Authoritative data is pinned | `data/banking77_source_manifest.json` | PolyAI commit `57ec275...`, 3 files with SHA-256, CC-BY-4.0 | Reject silent mirrors/repackages |
| Full Banking77 foundation is present | `reports/week_01/results/banking77_data_audit.json` | 13,083 samples, 77 intents | Use full taxonomy for Week 1 |
| Test remains frozen | `data/banking77_split_manifest.json` | 8,998 train / 1,005 validation / 3,080 test | Tune only on validation |
| Split is reproducible | W1-001 `verify` output and manifest | Combined membership SHA-256 `baa3d31f...c902`; rerun matches | Require same manifest in W1-002/W1-003 |
| Leakage risk is visible | W1-001 audit note | 0 exact overlap; 7 normalized label-consistent overlaps | Preserve official source; slice in W1-004 |

## Important data findings

- No missing/empty text or label, invalid label, exact duplicate, exact conflicting
  label, or exact official train/test overlap was found.
- Official train is imbalanced (35–187 examples per intent); official test has 40
  examples per intent.
- Validation contains every intent with 4–19 examples per intent.
- Short inputs exist: 9 examples have at most 2 tokens and 49 have at most 3.

## P0 exit criteria
- [x] W1-001 data audit and deterministic locked split.
- [ ] W1-002 lexical baseline.
- [ ] W1-003 semantic/model-based baseline.
- [ ] W1-004 evaluation, confusion/error analysis, and Week 1 gate.

## Risks / limitations
- Seven normalized official-boundary overlaps are a known evaluation limitation.
- No model result exists yet; Week 1 P0 gate remains open.

## Handoff
- Queue W1-002 only. It must verify and consume `banking77_w1_v1` unchanged.
- Do not start W1-002 without separate user authorization.

---

<!-- Source: reports/week_01/daily/2026-07-23.md -->

# Daily Report — 2026-07-23

## 1. Goal

Complete only `W1-001`: acquire the mentor-provided authoritative Banking77
files, audit actual integrity, and lock one deterministic data protocol shared by
future W1-002/W1-003 runs.

## 2. Tasks

- `W1-001` — completed with reproducibility, integrity, split, and test evidence.
- `W1-002` — not started; queued only.

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
- Performed no model training, benchmark evaluation, W1-002/W1-003 work, P1, or
  Week 2 work.

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
```

Results:

- Tests: 12/12 passed on Python 3.11.9.
- Project/report/public-safety validation: passed.
- Two consecutive audit-lock runs were byte-identical across all four generated
  provenance/split/audit outputs (`match=True`).
- Deterministic `verify`: passed raw checksums and exact regenerated artifact bytes.
- Dataset/model metrics: none; W1-001 is data preparation only.

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

## 7. Decisions / trade-offs

- Official test boundary takes precedence over random re-splitting.
- Hash ordering replaces library RNG so membership is stable across environments.
- Full membership IDs are committed without raw text so downstream tasks can
  verify the exact protocol while raw payloads remain ignored.
- Near-duplicate work stops at lightweight normalization; fuzzy deduplication
  would widen W1-001 without a demonstrated need.

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

## 9. Risks / blockers

- Seven label-consistent normalized train/test overlaps may make aggregate test
  results slightly optimistic; report the slice in W1-004.
- Exhaustive semantic annotation review was not performed; suspected ambiguity is
  handled through later confusion/error analysis.
- No blocker remains for W1-001. W1-002 requires separate user authorization.

## 10. Next step

- Stop. Queue `W1-002` without executing it.

## Suggested commit message

`feat(data): audit and lock Banking77 split`

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
