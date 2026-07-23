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

