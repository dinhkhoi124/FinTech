# W3-001-CR1 Evidence Gate Utility Recovery v2

## Status

Implementation DONE / REVIEWED / ACCEPTED. Original frozen-mapping evaluation:
FAILED — INVALIDATED BY INCOMPLETE RELEVANCE MAPPING. Post-hoc adjudicated
evaluation: PASS / REVIEWED / ACCEPTED. Senior verdict: `APPROVE_COMMIT —
QUALIFIED POST-HOC PASS`. W3-002 is QUEUED / NOT STARTED; Week 4 remains NOT STARTED.

## Root-cause hypothesis

Gate v1 uses exact IDF token coverage as a hard threshold. It may underestimate
support when customer language and approved evidence use different surface forms,
including processing versus pending, refused/rejected versus declined,
undone/returned versus reverted, cash machine versus ATM, and recipient-credit
paraphrases.

Lowering the v1 coverage threshold alone is not expected to be sufficient because
an unsupported specific-detail query can still overlap strongly with generic
approved evidence. Evidence Gate v2 therefore preregisters four changes:

1. canonicalized support matching for common banking paraphrases;
2. requested-information-dimension matching;
3. an unsupported-specificity guard;
4. a fresh frozen holdout so recovery is not judged only on observed design cases.

This diagnosis is a hypothesis, not a result, until the controlled experiment runs.

## Controlled experiment

- Design/tuning: unchanged W3-001 20-case set, relabeled `gate_v2_design`.
- Holdout: 20 new cases, exactly ten ANSWER and ten ABSTAIN_ESCALATE.
- Fixed: R0, top-k 3, approved/effective filtering, extractive generator,
  claim/citation verifier, override guard, ambiguity gap 0.03, diagnostic-only
  predicted intent.
- Changed: deterministic canonical sentence support, requested dimension, and
  unsupported-specificity guard.
- Selection: frozen 3 × 3 candidate grid on design only.
- Acceptance: zero safety violations on design and holdout; holdout positive
  grounded recall at least 0.50, all three intent families represented, negative
  abstention 1.00, and safe resolution at least 0.75.

## Stop rules

- No eligible design candidate: FAILED / BLOCKED.
- Holdout mapping defect discovered after freeze: stop without repair/rerun.
- Any hard safety violation: FAILED; W3-002 remains blocked.
- Holdout utility below target with safety preserved: PARTIAL; do not tune v2.

## Recovery and execution record

- The first holdout attempt before system restart stopped while loading the frozen
  MiniLM encoder because Windows committed memory was exhausted (`os error 1455`).
  It produced no rankings, outputs, or holdout metrics.
- After restart, Git HEAD remained synchronized at
  `b6a7249defe0ea15ef997e502500936da962e8a7`; the selected policy, config,
  lexicon, holdout, selection, and pre-holdout hashes all matched the frozen
  filesystem evidence.
- The first post-restart launch loaded the encoder but exposed a runtime-only
  `split` metadata adapter defect before any canonical artifact was written. The
  fix adds `split=holdout` to an in-memory query copy and does not modify frozen
  JSONL/config/policy bytes. A regression test protects that boundary.
- The formal primary and one reproduction then completed. Outputs are
  byte-identical; no additional evaluation run or post-holdout tuning occurred.

## Frozen selection

- Candidate: `S0.40_C0.20`
- `min_top1_score`: 0.40
- `min_best_sentence_support_coverage`: 0.20
- `ambiguity_score_gap`: 0.03
- Holdout IDs used for selection: 0
- Selection SHA-256:
  `b17cee0c976552d14eec940f9bb81d95bb2ba9731b615295ab6be10313606469`
- Pipeline config SHA-256:
  `9319799a704ddbc82e824f7351adc3852672e4b277efea2fc0bc552ef4f518f2`

## Holdout results

| Metric | Gate v1 | Gate v2 | Delta |
|---|---:|---:|---:|
| ANSWER count | 1 | 7 | +6 |
| Positive relevant answers | 1/10 | 6/10 | +5 |
| Positive grounded recall | 0.10 | 0.60 | +0.50 |
| Safe resolution accuracy | 0.55 | 0.80 | +0.25 |
| Negative abstention accuracy | 1.00 | 1.00 | 0.00 |
| Unsafe-answer rate | 0.00 | 0.00 | 0.00 |
| Positive wrong-evidence answers | 0 | 1 | +1 |
| Unsupported claims | 0 | 0 | 0 |
| Citation metadata failures | 0 | 0 | 0 |

Gate v2 produced positive resolutions in all required families: transfer,
card_payment, and cash_withdrawal. Citation correctness on answered cases was
1.00; all 21 claims were supported by their cited approved sections, and no
DRAFT/EXPIRED citation entered an answer.

The hard failure is `Q_V2_HOLD_TR_PEND_001`. Its requested dimension is
`TIMING_WINDOW`, but the answer cited `POL_TRANSFER_PENDING_002#eligibility`,
`RUN_TRANSFER_PENDING_001#action`, and `RUN_TRANSFER_PENDING_001#checks` rather
than its strict gold/acceptable timing sections
`POL_TRANSFER_PENDING_002#current_window` or
`FAQ_TRANSFER_PENDING_001#customer_boundary`. The evidence is approved and
same-intent, but it is wrong under the frozen query-level relevance contract.

## Mapping adjudication

The original verdict remains `FAILED`: one generated positive answer did not
overlap the incomplete relevance mapping. A comprehensive audit then reviewed all
ten positive queries against all 52 eligible approved sections and found three
clerical omissions (3/10). Senior accepted exactly those three corrections.

The immutable original dataset is paired with a three-row overlay that only adds
acceptable evidence during post-holdout relevance metric recomputation. It does
not change a query, ranking, output, citation, policy, threshold, gate decision,
claim, or generation. Original primary/reproduction outputs retain SHA-256
`06fe9075650f463b9e9c019c4fef73ce3f1e91fc94e7c430dc69819b702c37fe`.

| Metric | Gate v1 | Gate v2 original | Gate v2 adjudicated |
|---|---:|---:|---:|
| ANSWER count | 1 | 7 | 7 |
| Positive relevant answers | 1 | 6 | 7 |
| Positive wrong-evidence answers | 0 | 1 | 0 |
| Positive grounded recall | 0.10 | 0.60 | 0.70 |
| Safe resolution accuracy | 0.55 | 0.80 | 0.85 |
| Negative abstention accuracy | 1.00 | 1.00 | 1.00 |
| Unsafe-answer rate | 0.00 | 0.00 | 0.00 |

Adjudicated Gate v2 passes both hard safety and utility requirements. It retains
zero unsupported claims, citation metadata failures, DRAFT citations, and EXPIRED
citations. The limitation is explicit: this is a post-hoc adjudicated evaluation,
not a pristine untouched-label evaluation, a final Week 3 safety pass, or a
production-ready gate. W3-002 is QUEUED / NOT STARTED.

## Verification

- KB, gold mapping, W2 retrieval, W3-001 v1, and CR1 tracked verifiers: PASS.
- CR1 focused tests: 65/65 PASS.
- Full repository tests: 289/289 PASS.
- KB, gold mapping, retrieval, W3-001, and adjudication tracked verifiers: PASS.
- Project docs validator and `git diff --check`: PASS.
