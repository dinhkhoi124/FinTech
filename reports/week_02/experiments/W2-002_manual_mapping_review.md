# W2-002 — Structured Manual Mapping Review

## Review status and root cause

The initial construction review reported 60/60 rows as accepted. Senior review
correctly found that this result was too weak and it is retained here rather than
hidden.

The first validator proved reference existence, eligibility, counts, hashes, role
disjointness, and coverage, but did not prove that primary gold directly answered
the requested factual dimension. Several rows therefore used an intent-defining
section where the query requested timing, checks, action, retry, or escalation.
The first safety design also treated reliance on DRAFT/EXPIRED wording as automatic
no-evidence, even where approved evidence could give a corrective factual answer.

This remains a structured construction review by Codex, not independent human
annotation. Senior final review accepted the corrected mapping with verdict
`APPROVE_COMMIT`.

## Correction summary

- Rows in canonical correction ledger: 60.
- ANSWER rows direct-support audited: 50/50.
- Evidence-role mappings unchanged: 41/60 (31 ANSWER plus 10 safety).
- Primary gold roles changed: 19.
- Acceptable roles changed: 19.
- Query texts rewritten/replaced: 12 (2 ANSWER and 10 safety).
- Safety probes replaced: 10/10.
- Mapping rationales replaced: 60/60.
- Hard-negative rationales replaced: 60/60.
- Initial 60/60 construction-review outcome: superseded, not deleted.

For ANSWER rows, primary gold now names and supports the requested dimension.
For safety rows, the new wording requests a precise unsupported detail and the
rationale names approved sections checked, their limitation, and why the
DRAFT/EXPIRED section remains attractive but forbidden.

## Correction ledger

The machine-readable source is
`data/evaluation/gold_mapping_correction_ledger_v1.jsonl`.

| Query ID | Review finding | Old primary gold | New primary gold | Query correction | Reason |
|---|---|---|---|---|---|
| Q_DEV_CARD_DECL_001 | primary lacked direct support | FAQ_CARD_DECLINED_001#answer | RUN_CARD_DECLINED_001#checks | unchanged | Primary gold now directly answers agent checks; rationale names the requested dimension and supporting fact. |
| Q_DEV_CARD_PEND_001 | rationale/direct-support confirmation | FAQ_CARD_PENDING_001#answer | FAQ_CARD_PENDING_001#answer | unchanged | Primary gold now directly answers state/definition; rationale names the requested dimension and supporting fact. |
| Q_DEV_CARD_REVERT_001 | primary lacked direct support | POL_CARD_REVERT_002#state_rule | POL_CARD_REVERT_002#return_window | unchanged | Primary gold now directly answers timing/window; rationale names the requested dimension and supporting fact. |
| Q_DEV_CASH_DECL_001 | primary lacked direct support | POL_CASH_DECLINED_001#eligibility | POL_CASH_DECLINED_001#review_rule | unchanged | Primary gold now directly answers escalation trigger; rationale names the requested dimension and supporting fact. |
| Q_DEV_CASH_PEND_001 | primary lacked direct support | FAQ_CASH_PENDING_001#answer | RUN_CASH_PENDING_001#pending_action | unchanged | Primary gold now directly answers timing and customer action; rationale names the requested dimension and supporting fact. |
| Q_DEV_CASH_UNREC_001 | primary lacked direct support | POL_CASH_UNRECOG_001#security_rule | ESC_CASH_UNRECOG_001#immediate_trigger | unchanged | Primary gold now directly answers escalation trigger; rationale names the requested dimension and supporting fact. |
| Q_DEV_TR_DECL_001 | primary lacked direct support | FAQ_TRANSFER_DECLINED_001#answer | FAQ_TRANSFER_DECLINED_001#safe_message | unchanged | Primary gold now directly answers customer-facing action; rationale names the requested dimension and supporting fact. |
| Q_DEV_TR_FAIL_001 | rationale/direct-support confirmation | FAQ_TRANSFER_FAILED_001#retry_boundary | FAQ_TRANSFER_FAILED_001#retry_boundary | unchanged | Primary gold now directly answers retry rule; rationale names the requested dimension and supporting fact. |
| Q_DEV_TR_PEND_001 | primary lacked direct support | FAQ_TRANSFER_PENDING_001#answer | FAQ_TRANSFER_PENDING_001#customer_boundary | unchanged | Primary gold now directly answers timing and customer action; rationale names the requested dimension and supporting fact. |
| Q_DEV_TR_RECIP_001 | primary lacked direct support | FAQ_TRANSFER_RECIPIENT_002#meaning | FAQ_TRANSFER_RECIPIENT_002#current_window | unchanged | Primary gold now directly answers timing and tracing action; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_DECL_001 | rationale/direct-support confirmation | RUN_CARD_DECLINED_001#checks | RUN_CARD_DECLINED_001#checks | unchanged | Primary gold now directly answers agent checks; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_DECL_002 | primary lacked direct support | FAQ_CARD_DECLINED_001#answer | RUN_CARD_DECLINED_001#checks<br>RUN_CARD_DECLINED_001#action | unchanged | Primary gold now directly answers agent checks and safe action; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_DECL_003 | rationale/direct-support confirmation | FAQ_CARD_DECLINED_001#answer | FAQ_CARD_DECLINED_001#answer | rewritten: My shop payment was refused. Which payment state is this? | Primary gold now directly answers state/definition; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_DECL_004 | rationale/direct-support confirmation | RUN_CARD_DECLINED_001#action | RUN_CARD_DECLINED_001#action | unchanged | Primary gold now directly answers agent action; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_PEND_001 | primary lacked direct support | POL_CARD_PENDING_001#eligibility | FAQ_CARD_PENDING_001#fictional_window | unchanged | Primary gold now directly answers timing/window; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_PEND_002 | rationale/direct-support confirmation | FAQ_CARD_PENDING_001#answer | FAQ_CARD_PENDING_001#answer | unchanged | Primary gold now directly answers state/definition; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_PEND_003 | rationale/direct-support confirmation | POL_CARD_PENDING_001#review_window | POL_CARD_PENDING_001#review_window | unchanged | Primary gold now directly answers timing/window; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_PEND_004 | primary lacked direct support | RUN_CARD_PENDING_001#action | RUN_CARD_PENDING_001#checks | unchanged | Primary gold now directly answers agent checks; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_REVERT_001 | rationale/direct-support confirmation | POL_CARD_REVERT_002#return_window | POL_CARD_REVERT_002#return_window | unchanged | Primary gold now directly answers timing/window; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_REVERT_002 | rationale/direct-support confirmation | POL_CARD_REVERT_002#state_rule | POL_CARD_REVERT_002#state_rule | unchanged | Primary gold now directly answers eligibility and state boundary; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_REVERT_003 | rationale/direct-support confirmation | ESC_CARD_REVERT_001#trigger | ESC_CARD_REVERT_001#trigger | unchanged | Primary gold now directly answers escalation trigger; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CARD_REVERT_004 | rationale/direct-support confirmation | POL_CARD_REVERT_002#return_window<br>ESC_CARD_REVERT_001#trigger | POL_CARD_REVERT_002#return_window<br>ESC_CARD_REVERT_001#trigger | unchanged | Primary gold now directly answers timing and escalation trigger; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_DECL_001 | rationale/direct-support confirmation | POL_CASH_DECLINED_001#eligibility | POL_CASH_DECLINED_001#eligibility | unchanged | Primary gold now directly answers eligibility; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_DECL_002 | primary lacked direct support | POL_CASH_DECLINED_001#eligibility | POL_CASH_DECLINED_001#review_rule | unchanged | Primary gold now directly answers review action; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_DECL_003 | rationale/direct-support confirmation | ESC_CASH_DECLINED_001#trigger | ESC_CASH_DECLINED_001#trigger | unchanged | Primary gold now directly answers escalation trigger; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_DECL_004 | rationale/direct-support confirmation | ESC_CASH_DECLINED_001#handoff | ESC_CASH_DECLINED_001#handoff | unchanged | Primary gold now directly answers safe handoff information; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_PEND_001 | rationale/direct-support confirmation | FAQ_CASH_PENDING_001#fictional_window | FAQ_CASH_PENDING_001#fictional_window | unchanged | Primary gold now directly answers timing/window; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_PEND_002 | primary and acceptable roles remained inverted after v2 review | RUN_CASH_PENDING_001#recognition_check | FAQ_CASH_PENDING_001#answer | unchanged | FAQ answer directly establishes recognition plus pending state; runbook recognition check supplies only the recognition gate and security fallback. |
| Q_LOCK_CASH_PEND_003 | rationale/direct-support confirmation | FAQ_CASH_PENDING_001#answer | FAQ_CASH_PENDING_001#answer | unchanged | Primary gold now directly answers state/definition; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_PEND_004 | primary lacked direct support | RUN_CASH_PENDING_001#pending_action | RUN_CASH_PENDING_001#recognition_check | unchanged | Primary gold now directly answers agent checks; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_UNREC_001 | rationale/direct-support confirmation | ESC_CASH_UNRECOG_001#immediate_trigger | ESC_CASH_UNRECOG_001#immediate_trigger | unchanged | Primary gold now directly answers escalation trigger; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_UNREC_002 | rationale/direct-support confirmation | RUN_CASH_UNRECOG_002#recognition_gate | RUN_CASH_UNRECOG_002#recognition_gate | unchanged | Primary gold now directly answers agent checks and prohibited workflow; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_UNREC_003 | rationale/direct-support confirmation | POL_CASH_UNRECOG_001#prohibited_actions | POL_CASH_UNRECOG_001#prohibited_actions | unchanged | Primary gold now directly answers prohibited action; rationale names the requested dimension and supporting fact. |
| Q_LOCK_CASH_UNREC_004 | rationale/direct-support confirmation | POL_CASH_UNRECOG_001#security_rule<br>RUN_CASH_UNRECOG_002#safe_handoff<br>ESC_CASH_UNRECOG_001#immediate_trigger | POL_CASH_UNRECOG_001#security_rule<br>RUN_CASH_UNRECOG_002#safe_handoff<br>ESC_CASH_UNRECOG_001#immediate_trigger | unchanged | Primary gold now directly answers security rule, handoff, and escalation trigger; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_DECL_001 | primary lacked direct support | POL_TRANSFER_DECLINED_001#eligibility | POL_TRANSFER_DECLINED_001#review_rule | unchanged | Primary gold now directly answers review action; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_DECL_002 | rationale/direct-support confirmation | FAQ_TRANSFER_DECLINED_001#answer | FAQ_TRANSFER_DECLINED_001#answer | unchanged | Primary gold now directly answers state/definition; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_DECL_003 | rationale/direct-support confirmation | POL_TRANSFER_DECLINED_001#review_rule | POL_TRANSFER_DECLINED_001#review_rule | unchanged | Primary gold now directly answers review trigger; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_DECL_004 | primary lacked direct support | RUN_TRANSFER_DECLINED_001#action | RUN_TRANSFER_DECLINED_001#checks | unchanged | Primary gold now directly answers agent checks; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_FAIL_001 | primary lacked direct support | POL_TRANSFER_FAILED_001#eligibility | RUN_TRANSFER_FAILED_001#checks | unchanged | Primary gold now directly answers agent checks before retry; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_FAIL_002 | rationale/direct-support confirmation | FAQ_TRANSFER_FAILED_001#answer | FAQ_TRANSFER_FAILED_001#answer | unchanged | Primary gold now directly answers state/definition; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_FAIL_003 | rationale/direct-support confirmation | POL_TRANSFER_FAILED_001#retry_rule | POL_TRANSFER_FAILED_001#retry_rule | rewritten: My transfer ended in an error. Can I safely try once more? | Primary gold now directly answers retry rule; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_FAIL_004 | rationale/direct-support confirmation | RUN_TRANSFER_FAILED_001#action | RUN_TRANSFER_FAILED_001#action | unchanged | Primary gold now directly answers retry and escalation action; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_PEND_001 | primary lacked direct support | POL_TRANSFER_PENDING_002#eligibility | FAQ_TRANSFER_PENDING_001#customer_boundary | unchanged | Primary gold now directly answers timing and customer action; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_PEND_002 | primary lacked direct support | FAQ_TRANSFER_PENDING_001#answer | FAQ_TRANSFER_PENDING_001#customer_boundary | unchanged | Primary gold now directly answers customer action and workflow; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_PEND_003 | rationale/direct-support confirmation | POL_TRANSFER_PENDING_002#current_window | POL_TRANSFER_PENDING_002#current_window | unchanged | Primary gold now directly answers timing/window; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_PEND_004 | rationale/direct-support confirmation | POL_TRANSFER_PENDING_002#current_window<br>RUN_TRANSFER_PENDING_001#action | POL_TRANSFER_PENDING_002#current_window<br>RUN_TRANSFER_PENDING_001#action | unchanged | Primary gold now directly answers timing and escalation action; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_RECIP_001 | rationale/direct-support confirmation | FAQ_TRANSFER_RECIPIENT_002#current_window | FAQ_TRANSFER_RECIPIENT_002#current_window | unchanged | Primary gold now directly answers timing/window; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_RECIP_002 | rationale/direct-support confirmation | POL_TRANSFER_RECIPIENT_001#eligibility | POL_TRANSFER_RECIPIENT_001#eligibility | unchanged | Primary gold now directly answers eligibility and workflow; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_RECIP_003 | rationale/direct-support confirmation | POL_TRANSFER_RECIPIENT_001#trace_window | POL_TRANSFER_RECIPIENT_001#trace_window | unchanged | Primary gold now directly answers tracing trigger; rationale names the requested dimension and supporting fact. |
| Q_LOCK_TR_RECIP_004 | rationale/direct-support confirmation | POL_TRANSFER_RECIPIENT_001#trace_window<br>ESC_TRANSFER_RECIPIENT_001#handoff | POL_TRANSFER_RECIPIENT_001#trace_window<br>ESC_TRANSFER_RECIPIENT_001#handoff | unchanged | Primary gold now directly answers timing and handoff; rationale names the requested dimension and supporting fact. |
| Q_SAFE_001 | invalid prior safety premise | [] | [] | rewritten: What priority tier and internal queue identifier will support assign if my transfer is still processing after exactly six hours? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |
| Q_SAFE_002 | invalid prior safety premise | [] | [] | rewritten: What percentage of a reversed card purchase is paid as provisional credit, and what repayment terms apply? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |
| Q_SAFE_003 | invalid prior safety premise | [] | [] | rewritten: Which device signals and scoring threshold automatically close an ATM withdrawal dispute that I do not recognize? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |
| Q_SAFE_004 | invalid prior safety premise | [] | [] | rewritten: What internal tracing queue code and guaranteed service time apply the instant a completed transfer is missing at the recipient? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |
| Q_SAFE_005 | invalid prior safety premise | [] | [] | rewritten: What compensation amount is guaranteed if my recognized ATM entry has not cleared within two hours? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |
| Q_SAFE_006 | invalid prior safety premise | [] | [] | rewritten: Which internal routing code and staff access level applied to the old transfer queue after a five-day wait? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |
| Q_SAFE_007 | invalid prior safety premise | [] | [] | rewritten: What legacy queue code and approval matrix were used to escalate a reversed card payment on day eight? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |
| Q_SAFE_008 | invalid prior safety premise | [] | [] | rewritten: What was the retired general ATM support queue ID and which internal form fields did it require for unknown cash withdrawals? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |
| Q_SAFE_009 | invalid prior safety premise | [] | [] | rewritten: Which internal trace case code and team SLA applied after the former four-day recipient wait? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |
| Q_SAFE_010 | invalid prior safety premise | [] | [] | rewritten: What compensation amount and override authorization code are guaranteed after a second refused shop payment? | Safety probe now requests a precise detail absent from both approved evidence and the attractive forbidden document. |

## Safety re-review

All ten new safety probes ask for a detail absent from both eligible evidence and
the attractive ineligible section: internal queue identifiers, access levels,
approval matrices, form schemas, automation thresholds, compensation amounts, or
unsupported entitlement terms. Approved sections can describe the current safe
workflow, but cannot supply a complete corrective factual answer to those exact
requests. Gold and acceptable lists remain empty, and each of the five DRAFT and
five EXPIRED documents remains represented once as forbidden evidence.

## Validator and mutation review

Hard negatives must now support `scenario.confusing_intent`, must not support
the gold intent, and remain eligible. Mapping string fields, evidence ID types,
query IDs/text, and scenario-plan structure/types/distributions are validated
independently of hashes.

Seven direct mutations all failed with their intended explicit codes; retained
output is `reports/week_02/results/gold_mapping_v1_direct_mutations.txt`.
Focused regression coverage increased from 29 to 43 tests.

Senior v2 review accepted every other correction and identified only
`Q_LOCK_CASH_PEND_002`. Its roles and rationale were patched without changing
query, scenario, hard negative, split, tags, or membership.

Final review verdict: `APPROVE_COMMIT`. W2-002 is DONE / REVIEWED / ACCEPTED.

## Leakage and limitations

After 12 query rewrites: exact and normalized duplicates are zero; near-duplicate
and query-to-KB candidates at token-Jaccard 0.72 are zero; Banking77 train and
official-test exact/normalized equality remain zero. Official-test text was not
printed or manually inspected.

Token Jaccard is lexical only. Direct-support review still has one construction
reviewer, and the synthetic KB is not real banking policy.
