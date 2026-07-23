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
