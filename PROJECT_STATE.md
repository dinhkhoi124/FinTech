# Project State

> This file is the concise handoff that every new Codex chat/session must read and update.

## Current status
- Project: PayResolve AI
- Current phase: Phase 2 — Controlled Synthetic KB + retrieval
- Current week: Week 2
- P0 gate status: PASSED
- Active task: none
- Next task: open Week 3 only through a separate reviewed task contract
- Last updated: 2026-07-28 by Codex

## Active objective
Week 2 P0 is complete and accepted. Keep Week 3 generation, the evidence gate,
API/UI, and P1 closed until a separate reviewed task contract opens Week 3.

## Current versions
- Current committed code baseline: W2-002 commit
  `76ff6162fb9ddb9a546f8a3f7862b62a8af83285`
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

## Completed
- [x] Repository bootstrap and reporting workflow
- [x] W1-001 authoritative source, audit, and deterministic locked split
- [x] W1-002 frozen lexical validation baseline
- [x] W1-003 frozen semantic validation baseline
- [x] W1-004 official-test benchmark, error analysis, model selection, and gate
- [x] Week 1 P0 gate passed
- [x] W2-001 controlled synthetic KB — DONE / REVIEWED / COMMITTED / PUSHED
- [x] W2-002 gold evidence mapping — DONE / REVIEWED / COMMITTED / PUSHED
- [x] W2-003 retrieval R0/R1 — DONE / REVIEWED / ACCEPTED
- [x] Week 2 P0 gate passed

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

## Next 3 actions
1. User runs the final pre-stage gate and commits/pushes only approved W2-003 paths.
2. Confirm clean synchronized `main` after push.
3. Open Week 3 only through a separate reviewed task contract.

## Handoff note
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
current working changes have not yet been staged, committed, or pushed. Week 3
is NOT STARTED.
