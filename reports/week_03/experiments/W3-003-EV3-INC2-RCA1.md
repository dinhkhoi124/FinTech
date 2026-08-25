# W3-003-EV3-INC2-RCA1 — official INVALID adjudication and Week-3 closure

## Scope

This is posthoc forensics only. EV3 authorization 0003 is consumed and the
official score is immutable. No inference, harness, scorer, re-score, EV4,
Gold, frozen raw, candidate, evaluator, mapping, or reason-compatibility bytes
were changed.

## Official locks and raw integrity

The official score remains `INVALID` at SHA-256
`e0fbe9ef139af79af53414c372141d6ce869c6ac35b007291c2d87ff887ab12e`.
The consumption receipt, raw output, and raw manifest retain their recorded
hashes. Raw integrity is 60 physical/valid JSON/unique IDs/row hashes with
exact case and query ordering; the historical raw-before-Gold result and score
reproducibility are both `PASS`.

## Root cause and independent safety signal

All 14 evaluator-integrity rows are fail-closed unknown reason codes: seven
`CONFLICTING_REQUESTED_STATES` and seven
`INCOMPLETE_REQUESTED_OBLIGATION_COVERAGE`. Both are deterministic production
emission paths in `assess_requested_target`, while the frozen EV2 mapping
contains neither exact nor bounded coverage and uses `FAIL_CLOSED`.

Separately, 19 distinct rows carry both
`unsafe_wrong_evidence_factual_answer` and `wrong_target_authorization`; their
intersection with the 14 evaluator-integrity rows is zero. Thus a mapping-only
repair could not establish P0 PASS, and no corrected official score was
computed.

## Release decision

Week-3 P0 is not passed and autonomous P0 or current-candidate agent assist is
not authorized. A safe degraded demo is authorized only for non-autonomous
research/demo use, with human/operator control, fail-closed factual grounding,
and no production-readiness or EV3 PASS claim. Future work must validate
`PRODUCTION_REASON_VOCABULARY subset-of EVALUATOR_REASON_MAPPING_COVERAGE`
before freezing any future independent evaluation.

## Terminal state

`EV3_OFFICIAL_INVALID_CLOSED_READY_FOR_SAFE_DEGRADED_DEMO_TRANSITION`.
No rerun, re-score, EV4, new Gold, or new holdout is authorized.
