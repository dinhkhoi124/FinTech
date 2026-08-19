# W3-003-RM1 — Post-EV1 Remediation RCA

## 1. Executive decision summary

RM1 establishes two production root causes with non-locked development evidence only.

1. **Over-abstention:** `assess_requested_target()` makes a terminal state-conflict decision from the top retrieved scope before evaluating whether a later candidate directly matches the requested state. Two answerable W3-001 development cases reproduce this path. A third positive case is blocked by the structural `NEXT_ACTION_DIRECT_ACTION_REQUIRED` rule; this third mechanism is a supported hypothesis for utility loss, not a proven semantic false negative.
2. **Evidence/case-scope alignment:** the STANDARD plan first selects dimension-matching evidence, then pads the plan with any evidence sharing the top intent scope. Standard generation emits up to one claim per selected chunk, and citation verification checks exact local support and eligibility but not requested-objective appropriateness. An isolated synthetic counterfactual reproduces an off-objective, locally supported, successfully verified claim.

The preferred RM2 direction is test-first and bounded: make requested-state evaluation candidate-aware, and require objective-bound STANDARD selection/claim construction. Do not lower global thresholds, weaken eligibility checks, or alter corrective safety obligations.

This is an investigation candidate, not a remediation implementation or product approval.

## 2. Evidence eligibility registry

| Artifact/set | Origin | Purpose/history | Locked/consumed | RM1 class | Reason |
|---|---|---|---|---|---|
| `configs/evaluation/w3_003_behavior_dev_v1.json` + `data/evaluation/w3_003_behavior_dev_v1.jsonl` | W3-003 R | Synthetic behavior regression, authored before EV1; explicitly development-only and non-independent | No | `ALLOWED_NON_LOCKED_DEV` | Tracked provenance says newly authored synthetic, 14 cases, no expected target used at runtime. |
| `data/evaluation/evidence_gate_dev_v1.jsonl` | W3-001 | Development membership: 10 answerable references and 10 safety probes | No | `ALLOWED_NON_LOCKED_DEV` | Previously used for gate development; not a holdout. |
| `reports/week_03/results/grounded_pipeline_dev_outputs.jsonl` | W3-001 | Already-resolved development queries and R0 rankings | No | `ALLOWED_NON_LOCKED_DEV` | Avoids resolving through broader mappings that contain locked rows. |
| `reports/week_03/results/evidence_gate_dev_classifier_predictions.jsonl` | W3-001 | Classifier diagnostics for the same development membership | No | `ALLOWED_NON_LOCKED_DEV` | Diagnostic only; classifier output is not consumed by V3. |
| `data/kb/kb_v1.jsonl` + retrieval config | W2/W3 product corpus | Approved/effective synthetic KB and deterministic corpus contract | No | `ALLOWED_NON_LOCKED_DEV` | Product source corpus, not evaluation labels. |
| Existing V3 unit/regression fixtures | R/C1/C2 | Routing, corrective, grounding and safety invariants | No | `ALLOWED_NON_LOCKED_DEV` | Source-controlled synthetic fixtures. |
| W3-001-CR1 observed holdout and its resolved results | W3-001-CR1 | Previously consumed utility-recovery holdout | Yes | `LOCKED_OR_CONSUMED_EXCLUDED` | Consumption overrides a filename or later “development” label. The helper `run_nonlocked_regression()` was not run. |
| W2 critical/locked/holdout evaluations | W2 | Historical product/critical evaluation | Yes | `LOCKED_OR_CONSUMED_EXCLUDED` | Not valid remediation evidence. A broad schema-search command transiently printed rows from this excluded family; those rows were discarded and were not used in runtime diagnosis or probes. |
| EV1 independent queries/gold/scenarios/support/obligations/raw/evaluation and NB1 notebook cases | W3-003 EV1/NB1 | Consumed independent evaluation and reporting | Yes | `LOCKED_OR_CONSUMED_EXCLUDED` | Individual content is forbidden. None was opened, printed, replayed, or used by RM1. |
| Other artifacts whose development provenance was not proven | Various | Unknown | Uncertain | `UNCERTAIN_EXCLUDED` | Fail closed on provenance. |

## 3. V3 decision graph

| Stage | Control | Level | Gate / output |
|---|---|---|---|
| Classifier diagnostic | historical classifier output only | intent | Not passed to `run_case_v3()`; cannot directly control V3 routing. |
| R0 retrieval input | tracked W3-001 development output; production retriever upstream | section | Ordered chunk IDs/scores enter V3. |
| Eligible candidate pool | `pipeline_v3.attach_runtime_candidate_pool()` | section | APPROVED/effective filter, then maximum 3 STANDARD candidates. |
| Requested target | `routing_v3.assess_requested_target()` | query/intent/section | Override/private block; no evidence; top-scope state conflict; ambiguity; specificity; top1 >= 0.40; dimension/direct canonical coverage >= 0.20; timing/action guards. |
| STANDARD eligibility | `pipeline_v3.build_response_plan()` + `routing_v3.select_supported_standard_evidence()` | section | Requires `SUPPORTED`; selection uses dominant intent-scope coherence and dimension match/coverage. |
| STANDARD padding | `pipeline_v3.build_response_plan()` | intent/section | Adds remaining candidates sharing dominant scope until `max_evidence=3`, without rechecking requested dimension/objective. |
| CORRECTIVE eligibility | `run_case_v3()` | query/control plane | Entered only for `BLOCKED_CONTROL_PLANE`, never ordinary `UNSUPPORTED`. |
| CORRECTIVE discovery | `retrieval.runtime.discover_corrective_candidates()` + `corrective_v1` | intent/section/objective | Safe query/evidence scope anchor, bounded scan 128/pool 8, mandatory objective completeness; incomplete plans abstain. |
| TRUE ABSTAIN | `build_response_plan()` / `_abstain()` | response | Any ordinary `UNSUPPORTED`, missing safe anchor, incomplete corrective plan, empty target selection, or generation/verification failure. |
| Claim construction | `TargetedExtractiveGenerator`; STANDARD delegates `ExtractiveEvidenceGenerator` | claim | STANDARD selects sentence by query overlap + chunk score and emits up to one claim per selected chunk. CORRECTIVE is explicitly objective-conditioned. |
| Citation verification | `citations.verify_draft()` | claim/section | Exact quote, selected evidence, APPROVED/effective, metadata integrity, alias integrity. No requested-objective check. |
| Final response | `run_case_v3()` | response | STANDARD/CORRECTIVE answer or fail-closed abstention. |

The classifier is therefore a diagnostic side channel, not the first V3 decision stage. The first runtime-controlling inputs are retrieval rankings and eligible chunk metadata.

## 4. Non-locked dev baseline

- Synthetic W3-003 suite: 14/14 expected routes, `PASS`; 2 STANDARD, 7 CORRECTIVE, 5 ABSTAIN; zero citation failures; zero ineligible selections; no network calls.
- W3-001 development membership: 20 cases (10 answerable, 10 safety probes). Current V3 emitted answers for 7/10 answerable cases and abstained on 3/10. All 10 safety probes resolved through CORRECTIVE or ABSTAIN; none became STANDARD.
- Relevance recall is intentionally not claimed for this replay because the development membership file does not contain resolved gold evidence IDs. Emission and routing counts are the valid measurements.
- Classifier diagnostic: 11/20 predictions correct; only 1/3 positive abstentions had a correct classifier prediction. This does not establish classifier causality because V3 never consumes those predictions.
- Tests: 23/23 allowlisted V3 and W3-003 safety `unittest` cases passed. The consumed-holdout helper test was deliberately excluded. Full suite was not run because it includes locked/consumed evaluation tests; the local environment also lacks pytest and no dependency installation was authorized.

## 5. Over-abstention reproduction

Three answerable W3-001 development cases became ABSTAIN at the requested-target stage.

| First blocking mechanism | Count | Trace | Causality |
|---|---:|---|---|
| Top-1 `EVIDENCE_TARGET_STATE_CONFLICT` | 2 | The top retrieved evidence scope conflicts with the requested state even though a later top-3 item has the matching state/scope. The function returns before candidate-aware target selection. | `PROVEN` for reachability loss and first blocking point. |
| `NEXT_ACTION_DIRECT_ACTION_REQUIRED` | 1 | Retrieved same-scope checks/eligibility exist, but no sentence passes the direct-action structural rule; STANDARD is unreachable and ordinary UNSUPPORTED has no recovery path. | `SUPPORTED_HYPOTHESIS` for an unnecessary abstention because semantic answer completeness was not independently labeled. |

Factor verdicts:

- A. Classifier wrong/weak: `NOT_ESTABLISHED` as a V3 cause; contradicted as a direct cause because classifier fields are absent from `run_case_v3()`.
- B/F. Useful retrieval exists but top-scope conflict discards later support before selection: `PROVEN` on two development cases.
- C/H. Canonical/lexical detector failure: `SUPPORTED_HYPOTHESIS` only for the direct-action case; no isolated lexical defect was proven.
- D/G. STANDARD structural gate plus no ordinary-UNSUPPORTED recovery makes response unreachable: `PROVEN` as control flow; whether every blocked response should answer is not established.
- E. CORRECTIVE recovery failure: `NOT_ESTABLISHED`; these positive cases never enter corrective discovery because only control-plane blocks can do so.
- I. Unexpected defect: objective-insensitive STANDARD padding, covered below.

## 6. Evidence-scope reproduction

An isolated counterfactual copied only the allowed synthetic `RM1_DEV_STANDARD_CHECKS` fixture and added one APPROVED/effective chunk with the same `pending_card_payment` scope but a STATE claim rather than a CHECKS claim. No threshold or production file changed.

Observed path:

1. Requested dimension `CHECKS` was supported by the original checks chunk.
2. `select_supported_standard_evidence()` selected that supporting chunk.
3. `build_response_plan()` padded the plan with the same-scope state chunk.
4. STANDARD generation emitted one exact claim from each selected chunk.
5. `verify_draft()` passed both claims because both were exact, selected, eligible citations.

The off-objective state claim was therefore selected, cited, and verified. Production currently guarantees **locally supported claims from eligible selected evidence**, not the stronger **claims supported by evidence appropriate for the requested objective**. Causality level: `PROVEN`.

## 7. Root-cause table

| Cause | Evidence | Level | Affected stage | Safety implication |
|---|---|---|---|---|
| Top-1-only state conflict returns before candidate-aware support selection | 2/3 positive development abstentions; later matching-state evidence present; direct control path | `PROVEN` | requested target | Removing the guard blindly can answer from the wrong top1; remediation must select only matching-state direct support. |
| Ordinary `UNSUPPORTED` has no bounded recovery/clarification path | All 3 positive abstentions terminate; corrective is control-plane-only | `PROVEN` control-flow fact; `SUPPORTED_HYPOTHESIS` as a remediation target | response plan | Broad fallback could erode fail-closed behavior; any recovery must require direct objective support. |
| NEXT_ACTION requires direct-action lexical support despite same-scope checks/eligibility | 1 positive development abstention | `SUPPORTED_HYPOTHESIS` | requested target | Relaxation may emit incomplete action guidance. Needs explicit obligation tests, not threshold lowering. |
| STANDARD same-scope padding bypasses requested-objective filtering | Synthetic one-factor reproduction | `PROVEN` | selection | Eligible/local support is insufficient to prevent case-scope misalignment. |
| STANDARD generator and verifier lack objective binding | Source trace plus successful off-objective claim | `PROVEN` | claim + verifier | Citation correctness can coexist with semantically inappropriate claims. |
| Classifier error causes V3 abstention | Classifier is not a V3 runtime input | `NOT_ESTABLISHED` | classifier | Changing classifier would not fix these V3 gates. |
| Global 0.40/0.20 thresholds are root cause | No isolated non-locked evidence | `NOT_ESTABLISHED` | requested target | Threshold tuning would be unjustified and risks unsafe answers. |

## 8. Counterfactual diagnostics

### Requested-target verdict bypass — DIAGNOSTIC ONLY

For each of the three positive development abstentions, the harness preserved query, rankings, chunks, thresholds, selection, generator and verifier, and changed only the returned requested-target status to `SUPPORTED`. All 3/3 emitted STANDARD answers. This proves the verdict is the causal reachability gate. It does **not** prove those answers are semantically correct; in particular, bypassing state conflict can cite the wrong top1 evidence and is not a remediation proposal.

### Same-scope off-objective evidence — DIAGNOSTIC ONLY

Adding one same-scope state chunk to the checks fixture caused it to be selected, claimed, cited, and verified. This isolates the padding/generation/verifier gap without EV1 content or a persisted config change.

## 9. Unknowns / rejected hypotheses

- Top-k classifier effects are unknown upstream; only top1 prediction/confidence was present in allowed historical diagnostics, and classifier output is not consumed by V3.
- Exact semantic relevance/complete-cover recall for the 20-case replay was not recomputed because resolved development gold evidence was not present in the allowlisted membership artifact.
- No claim is made that all ordinary UNSUPPORTED cases should enter CORRECTIVE; current separation protects control-plane safety.
- No global threshold change is justified.
- No defect was established in approved/effective filtering, corrective pool bounds, exact-quote verification, or deterministic behavior.

## 10. Remediation options

### PREFERRED — Candidate-aware target binding plus objective-bound STANDARD claims

- Mechanism: evaluate requested state/dimension against each eligible candidate before declaring state conflict; select only coherent direct support for the requested target. Remove broad same-scope padding or require each padded chunk/claim to satisfy an explicit requested objective.
- Benefit: addresses both proven root-cause families.
- Safety risk: candidate fallback could select a lower-ranked but wrong section; mitigate with direct state/dimension support, ambiguity rejection, and unchanged eligibility/top1 safety floors.
- Regression risk: fewer supplemental claims and changed evidence order.
- Likely code: `routing_v3.py`, `pipeline_v3.py`, `targeted_extractive.py`; tests first in the existing V3/safety test files.
- Evidence basis: `PROVEN`; no EV1 wording or per-case labels.

### ALTERNATIVE — Selection-only hardening

- Mechanism: remove same-scope padding and leave requested-target state logic unchanged.
- Benefit: closes the proven evidence-scope gap with the smallest code surface.
- Risk: does not recover proven top1-conflict over-abstentions and may reduce answer breadth.
- Evidence basis: `PROVEN` for scope, incomplete for Family A.

### REJECTED / NOT JUSTIFIED — Lower canonical or retrieval thresholds / global answer fallback

- Benefit: may increase answer count.
- Risk: bypasses direct-support and fail-closed invariants; does not fix objective binding.
- Evidence basis: `NOT_ESTABLISHED`; would be threshold tuning without causal evidence.

## 11. Preferred RM2 scope

Proposed implementation contract, not authorized here:

- Root causes: top1-only state conflict before candidate-aware support; objective-insensitive STANDARD padding/claims.
- Test-first files: `tests/test_grounded_pipeline_v3.py`, `tests/test_w3_003_behavior_safety.py`.
- Likely source files: `src/payresolve_ai/generation/routing_v3.py`, `pipeline_v3.py`, and only if required `targeted_extractive.py`.
- Allowed acceptance data: the 14-case W3-003 synthetic development fixture, the 20-case W3-001 development membership using already-resolved rankings, synthetic mutation/property tests, and approved KB contract.
- Success: recover the two matching-state development traces only when direct target support is proven; never select/generate an off-objective STANDARD claim; 0 negative STANDARD answers; 0 unsupported/ineligible claims; deterministic repeat; existing allowlisted safety tests pass.
- Out of scope: threshold tuning, classifier retraining, KB changes, corrective obligation weakening, EV1 replay/use, new holdout, EV2, lifecycle publication, W4.

## 12. Regression strategy

1. Add a failing test where top1 has a conflicting state and rank2 has unambiguous direct requested-state support; assert only the matching candidate can be selected.
2. Add ambiguity and no-direct-support twins; both must remain fail closed.
3. Add a same-intent/different-objective chunk; assert it is neither selected nor claimed.
4. Assert every STANDARD claim binds to a declared requested objective in addition to exact citation support.
5. Re-run the 14 synthetic cases and the allowlisted 20-case development replay.
6. Preserve control-plane corrective completeness, no prohibited disclosure, approved/effective filtering, exact citation verification, deterministic output, and no network/model configuration.

## 13. Future independent-eval boundary

Even if RM2 later passes all development/regression evidence, W4 remains blocked. A future product-gate evaluation must be separately authored, distinct from remediation data, overlap-audited, frozen, Senior-reviewed, execution-authorized, run one-shot, and independently reviewed. RM1 did not author or execute EV2.

## 14. Explicit anti-EV1-contamination statement

- EV1 query text viewed/printed by the RM1 workflow: 0.
- EV1 query IDs used as development examples: 0.
- EV1 raw runtime/reproduction rows used: 0.
- EV1 per-case outcomes used: 0.
- EV1 gold/support/scenario/obligation rows used: 0.
- EV1 thresholds changed: 0.
- EV1-derived development probes created: 0.
- EV1 reruns: 0.
- Only aggregate canonical Markdown facts named in the task contract were used.

The scratch diagnostics were offline, used allowlisted development sources, changed no production source/config/test, and created no model candidate.
